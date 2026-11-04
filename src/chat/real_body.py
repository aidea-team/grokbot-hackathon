"""The real Go1 behind a deterministic safety layer. Grok plans, this code decides, a human can always stop.

Used by the chat app only when it was launched by a human with `--real` and the human typed `go` in the
terminal, and then only after an explicit "arm" click in the browser. No agent, test or CI ever starts it.

Safety design (see .claude/skills/robot-safety and docs/hardware/llm-robot-architecture.md):
- whitelist: the model can only call `walk`, `turn`, `stand` (+ `finish`, which is not a motion). No jumps,
  flips, posture changes, raw velocities, DAMPING. Anything else is refused with {"ok": false, "error": ...};
- limits twice: min/max in the JSON schema the model sees (tool_specs) AND here in validate(). The schema is only
  a hint, validate() is the rule. The driver (src/dog/driver.py validate_walk) is a third, independent check;
- state machine: DISARMED -> IDLE <-> MOVING, and HALTED after a kill switch (needs an explicit new arm);
- one action at a time (a command while MOVING is refused), no queue of motions;
- geofence by dead reckoning: a walk whose projected end point leaves the radius around the start is refused;
- minimum battery at arm time;
- kill switch: kill() is lock-free for the motion (sets HALTED, calls driver.halt()) and independent of the LLM;
- watchdog: if the browser stops sending heartbeats while the dog moves, the dog is halted;
- JSONL log of every proposal, verdict, execution, kill.
Odometry is OPEN LOOP (commanded speed x time): an estimate, not a measurement.
"""
from __future__ import annotations

import math
import queue
import threading
import time
from typing import Callable

import cameras

WATCHDOG_S = 3.0  # no browser heartbeat for this long while moving -> halt
GEOFENCE_M = 2.0  # radius around the arming point
MIN_BATTERY = 20  # percent, at arm time

DISARMED, IDLE, MOVING, HALTED = "DISARMED", "IDLE", "MOVING", "HALTED"


class RealError(Exception):
    """Arming failed (no connection, low battery...)."""


def _num(desc: str, lo: float, hi: float) -> dict:
    return {"type": "number", "description": desc, "minimum": lo, "maximum": hi}


class RealBody:
    name = "real"
    TOOLS = ("walk", "turn", "stand")
    WALK_DIST = (-0.3, 0.5)  # m per call (backwards is shorter: the camera looks forward)
    WALK_SPEED = (0.05, 0.3)  # m/s (driver hard limit is 0.4)
    TURN_DEG = (-45.0, 45.0)  # degrees per call
    TURN_RATE = (10.0, 30.0)  # deg/s (driver hard limit is 0.6 rad/s = 34 deg/s)
    MIN_WALK_M, MIN_TURN_DEG = 0.05, 3.0

    def __init__(self, driver_factory: Callable, log, camera=None, geofence_m: float = GEOFENCE_M,
                 min_battery: int = MIN_BATTERY, watchdog_s: float = WATCHDOG_S,
                 extra_cameras: dict | None = None):
        """driver_factory(log) -> a driver with connect/walk/stop/halt/close (Go1Driver; MockDriver in tests).
        camera: an object with acquire()/release() and a .frame (latest JPEG bytes), e.g. cams.relay(1) (front).
        extra_cameras: {"down": relay(2), "side": relay(4)}: same names as src/sim/cameras.py."""
        self._factory, self.log, self.camera = driver_factory, log, camera
        self.cameras = {"front": camera, **(extra_cameras or {})}
        self.geofence_m, self.min_battery, self.watchdog_s = geofence_m, min_battery, watchdog_s
        self.state = DISARMED
        self.driver = None
        self.battery: int | None = None
        self.x = self.y = self.yaw = 0.0  # dead reckoning from the arming point (yaw 0 = initial heading)
        self.last_block = None  # same attributes as the simulator, so the agent code is shared
        self.last_stuck = self.last_crash = self.last_fell = False
        self._current: str | None = None
        self._done = 0
        self._q: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._heartbeat = time.monotonic()
        self._quit = threading.Event()
        self._threads: list[threading.Thread] = []
        self._cam_held = False

    # ------------------------------------------------------------------ what the model is allowed to see
    @classmethod
    def tool_specs(cls) -> dict[str, dict]:
        """Whitelisted tools with the same limits validate() enforces (name -> description + JSON schema)."""
        return {
            "walk": {
                "description": "Cammina in avanti (distanza positiva) o indietro (negativa) per un tratto BREVE, "
                               "poi si ferma da solo. Il cane è vero: avvicinati con prudenza, passi corti.",
                "parameters": {"type": "object",
                               "properties": {
                                   "distance_m": _num("Metri da percorrere: da -0.3 (indietro) a 0.5 (avanti)",
                                                      *cls.WALK_DIST),
                                   "speed_mps": _num("Velocità in m/s, da 0.05 a 0.3 (default 0.2)", *cls.WALK_SPEED)},
                               "required": ["distance_m"]},
            },
            "turn": {
                "description": "Gira su sé stesso di un angolo piccolo: gradi positivi = a sinistra, negativi = a destra.",
                "parameters": {"type": "object",
                               "properties": {
                                   "degrees": _num("Angolo in gradi, da -45 a 45", *cls.TURN_DEG),
                                   "rate_dps": _num("Velocità angolare in gradi/s, da 10 a 30 (default 25)",
                                                    *cls.TURN_RATE)},
                               "required": ["degrees"]},
            },
            "stand": {
                "description": "Resta fermo in piedi per un secondo (per osservare senza muoverti).",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }

    # ------------------------------------------------------------------ arming / disarming (human-triggered)
    def arm(self) -> dict:
        """Connect to the dog and enter IDLE. Raises RealError. Called only after the human confirmed."""
        with self._lock:
            if self.state in (IDLE, MOVING):
                return self.snapshot()
        self._event("real_arm_request")
        driver = self._factory(self.log)
        try:
            info = driver.connect()
        except ConnectionError as e:
            self._event("real_arm_failed", reason=f"connect: {e}")
            raise RealError(f"NON connesso: {e}") from e
        soc = info.get("soc") if isinstance(info, dict) else None
        if isinstance(soc, (int, float)) and soc < self.min_battery:
            driver.close()
            self._event("real_arm_failed", reason=f"battery {soc}% < {self.min_battery}%")
            raise RealError(f"Batteria al {soc}%: sotto il minimo del {self.min_battery}%. Non armo.")
        with self._lock:
            self.driver, self.battery = driver, soc
            self.x = self.y = self.yaw = 0.0
            self._current, self._heartbeat = None, time.monotonic()
            self.state = IDLE
        self._quit.clear()
        if not self._cam_held:
            self._cam_held = True
            for relay in self.cameras.values():
                if relay is not None:
                    relay.acquire()
        if not any(t.is_alive() for t in self._threads):
            self._threads = [threading.Thread(target=self._worker, daemon=True, name="real-worker"),
                             threading.Thread(target=self._watchdog, daemon=True, name="real-watchdog")]
            for t in self._threads:
                t.start()
        self._event("real_armed", battery=soc, geofence_m=self.geofence_m)
        return self.snapshot()

    def disarm(self) -> None:
        """Leave real mode: stop, close the driver. Safe to call in any state."""
        self.kill("disarm", halted=False)
        self._release_camera()
        with self._lock:
            self.state = DISARMED
        self._event("real_disarmed")

    def _release_camera(self) -> None:
        if self._cam_held:
            self._cam_held = False
            for relay in self.cameras.values():
                try:
                    if relay is not None:
                        relay.release()
                except Exception:  # noqa: BLE001
                    pass

    # ------------------------------------------------------------------ the agent-facing body interface
    def heartbeat(self) -> None:
        self._heartbeat = time.monotonic()

    def is_idle(self) -> bool:
        return self.state != MOVING and self._q.empty()

    def validate(self, name: str, args) -> tuple[bool, str, dict]:
        """Deterministic verdict: (ok, reason, clean_args). Independent of the model and of the schema."""
        if name not in self.TOOLS:
            return False, f"tool {name!r} non consentito sul cane vero (ammessi: {', '.join(self.TOOLS)})", {}
        if not isinstance(args, dict):
            return False, "gli argomenti devono essere un oggetto", {}
        spec = {"walk": {"distance_m", "speed_mps"}, "turn": {"degrees", "rate_dps"}, "stand": set()}[name]
        for key, value in args.items():
            if key not in spec:
                return False, f"{name}: argomento sconosciuto {key!r}", {}
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                return False, f"{name}.{key}: deve essere un numero finito", {}
        if self.state == DISARMED:
            return False, "cane non armato", {}
        if self.state == HALTED:
            return False, "cane FERMATO dal kill switch: serve un nuovo arm esplicito da parte di un umano", {}
        if self.state == MOVING or not self._q.empty():
            return False, "un'azione è già in corso (una alla volta)", {}
        if name == "stand":
            return True, "ok", {}
        if name == "walk":
            dist = float(args["distance_m"]) if "distance_m" in args else None
            if dist is None:
                return False, "walk: manca distance_m", {}
            speed = float(args.get("speed_mps", 0.2))
            if not self.WALK_DIST[0] <= dist <= self.WALK_DIST[1] or abs(dist) < self.MIN_WALK_M:
                return False, (f"walk: distance_m={dist:g} fuori limiti (|d| ≥ {self.MIN_WALK_M} e "
                               f"da {self.WALK_DIST[0]} a {self.WALK_DIST[1]})"), {}
            if not self.WALK_SPEED[0] <= speed <= self.WALK_SPEED[1]:
                return False, f"walk: speed_mps={speed:g} fuori limiti ({self.WALK_SPEED[0]}-{self.WALK_SPEED[1]})", {}
            nx, ny = self.x + dist * math.cos(self.yaw), self.y + dist * math.sin(self.yaw)
            if math.hypot(nx, ny) > self.geofence_m:
                return False, (f"walk: il punto di arrivo stimato ({nx:.2f}, {ny:.2f}) esce dal geofence di "
                               f"{self.geofence_m:g} m: scegli un'altra direzione"), {}
            return True, "ok", {"distance_m": dist, "speed_mps": speed}
        deg = float(args["degrees"]) if "degrees" in args else None  # turn
        if deg is None:
            return False, "turn: manca degrees", {}
        rate = float(args.get("rate_dps", 25.0))
        if not self.TURN_DEG[0] <= deg <= self.TURN_DEG[1] or abs(deg) < self.MIN_TURN_DEG:
            return False, (f"turn: degrees={deg:g} fuori limiti (|a| ≥ {self.MIN_TURN_DEG} e da "
                           f"{self.TURN_DEG[0]:g} a {self.TURN_DEG[1]:g})"), {}
        if not self.TURN_RATE[0] <= rate <= self.TURN_RATE[1]:
            return False, f"turn: rate_dps={rate:g} fuori limiti ({self.TURN_RATE[0]:g}-{self.TURN_RATE[1]:g})", {}
        return True, "ok", {"degrees": deg, "rate_dps": rate}

    def submit(self, name: str, args: dict | None = None) -> dict:
        args = args if args is not None else {}
        ok, reason, clean = self.validate(name, args)
        self._event("real_proposed", tool=name, args=args)
        self._event("real_verdict", tool=name, ok=ok, reason=reason)
        if not ok:
            return {"ok": False, "error": reason}
        label = f"{name}({', '.join(f'{k}={v:g}' for k, v in clean.items())})"
        with self._lock:
            if self.state != IDLE:  # re-check under the lock: a kill may have just happened
                return {"ok": False, "error": "cane non pronto (fermato o già in movimento)"}
            self.state, self._current = MOVING, label
        self._q.put((name, clean, label))
        return {"ok": True, "queued": label, "queue_length": 1}

    def kill(self, source: str = "web", halted: bool = True) -> None:
        """Kill switch. Does not wait for any lock held by the motion thread: sets HALTED, halts the driver."""
        driver = self.driver
        if halted and self.state != DISARMED:
            self.state = HALTED  # plain assignment: atomic, no lock
        if driver is not None:
            driver.halt()  # lock-free in the driver
        while not self._q.empty():
            try:
                self._q.get_nowait()
            except queue.Empty:
                break
        self._event("kill_switch", source=source, state=self.state)
        if driver is not None:
            threading.Thread(target=self._close_driver, args=(driver,), daemon=True, name="real-close").start()

    def clear(self) -> None:
        """Same name as the simulator's "stop everything": halts the dog only if it is actually moving
        (the Stop button calls kill() directly and always latches HALTED)."""
        if self.state == MOVING:
            self.kill("agent_abort")

    def capture(self, width: int = 512, height: int = 384, camera: str = "front",
                wait_idle: bool = False, timeout: float = 120.0) -> bytes | None:
        """Latest frame of one of the dog's cameras ("front"=cam1, "down"=cam2, "side"=cam4), or None if the
        relay has nothing. Same signature as DogSim.capture."""
        relay = self.cameras.get(cameras.get(camera).name)
        if relay is None:
            return None
        if wait_idle:
            deadline = time.monotonic() + timeout
            while not self.is_idle() and time.monotonic() < deadline:
                time.sleep(0.1)
        # front: wait a bit for the first frame; the others must not slow the step down when they are off
        deadline = time.monotonic() + (4.0 if cameras.get(camera).name == "front" else 1.5)
        while getattr(relay, "frame", None) is None and time.monotonic() < deadline:
            time.sleep(0.1)
        return getattr(relay, "frame", None)

    def reset_pose(self) -> None:
        """"Reset demo" on the real dog cannot move it back: it only zeroes the estimated odometry/geofence origin."""
        with self._lock:
            self.x = self.y = self.yaw = 0.0
        self._event("real_origin_reset")

    def set_time_scale(self, scale: float) -> None:  # simulator only
        pass

    def snapshot(self) -> dict:
        return {
            "x": round(self.x, 2), "y": round(self.y, 2),
            "yaw_deg": round(math.degrees(math.atan2(math.sin(self.yaw), math.cos(self.yaw)))),
            "z": None, "posture": "in piedi", "current": self._current, "queue": [], "done": self._done,
            "time_scale": None, "viewer": None, "estimated": True, "battery": self.battery,
            "real_state": self.state, "geofence_m": self.geofence_m,
        }

    # ------------------------------------------------------------------ threads
    def _worker(self) -> None:
        while not self._quit.is_set():
            try:
                name, args, label = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            driver = self.driver
            if driver is None or self.state != MOVING:
                continue
            self._event("real_exec_start", command=label)
            t0 = time.monotonic()
            try:
                if name == "walk":
                    vx = math.copysign(args["speed_mps"], args["distance_m"])
                    secs = abs(args["distance_m"]) / args["speed_mps"]
                    res = driver.walk(vx, 0.0, secs)
                    moved = vx * (res.elapsed_s if res.interrupted else secs)
                    self.x += moved * math.cos(self.yaw)
                    self.y += moved * math.sin(self.yaw)
                elif name == "turn":
                    vyaw = math.copysign(math.radians(args["rate_dps"]), args["degrees"])
                    secs = abs(args["degrees"]) / args["rate_dps"]
                    res = driver.walk(0.0, vyaw, secs)
                    self.yaw += vyaw * (res.elapsed_s if res.interrupted else secs)
                else:  # stand: stay still for 1 s (keeps sending idle)
                    t_end = time.monotonic() + 1.0
                    while time.monotonic() < t_end and not driver.halt_event.is_set():
                        driver.drive(0.0, 0.0)
                        time.sleep(0.02)
                    res = None
                self._event("real_exec_done", command=label, ok=bool(res.ok) if res else True,
                            reason=res.reason if res else "ok", elapsed_s=round(time.monotonic() - t0, 2),
                            x=round(self.x, 3), y=round(self.y, 3), yaw=round(self.yaw, 3))
            except Exception as e:  # noqa: BLE001 - any failure: stop and require a human
                self._event("real_exec_error", command=label, error=repr(e))
                self.kill("error")
            with self._lock:
                self._done += 1
                self._current = None
                if self.state == MOVING:
                    self.state = IDLE

    def _watchdog(self) -> None:
        while not self._quit.is_set():
            time.sleep(0.5)
            if self.state == MOVING and time.monotonic() - self._heartbeat > self.watchdog_s:
                self.kill("watchdog")

    def _close_driver(self, driver) -> None:
        if self.driver is driver:  # a new arm may already have replaced it: never touch the new one
            self.driver = None
        try:
            driver.close()  # sends idle for 0.5 s
        except Exception:  # noqa: BLE001
            pass

    def shutdown(self) -> None:
        self._quit.set()
        self.disarm()

    def _event(self, kind: str, **fields) -> None:
        if self.log is not None:
            try:
                self.log.event(kind, **{k: (v if isinstance(v, (int, float, str, bool, type(None), dict, list)) else repr(v))
                                        for k, v in fields.items()})
            except Exception:  # noqa: BLE001 - a logging problem must never block a safety decision
                pass
