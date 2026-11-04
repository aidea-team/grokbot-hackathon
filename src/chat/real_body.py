"""The real Go1 behind the kill switch. Grok plans, this code relays, a human can always stop.

Used by the chat app only when it was launched by a human with `--real` and the human typed `go` in the
terminal, and then only after an explicit "arm" click in the browser. No agent, test or CI ever starts it.

NO LIMITS ON PURPOSE (2026-11-04): all the numeric guardrails (distance/speed/angle ranges, geofence, minimum
battery, short-step prompts) were removed so the team can design them from a clean slate. What is left is not
a limit on what the dog may do, it is the machinery to stop it and to know who did what:
- all the Go1 primitives are exposed: walk, turn, stand, stand_up, lie_down, recovery, backflip, jump_yaw,
  straight_hand, dance (style 1|2), damping. Arguments are only checked for type (finite numbers);
- state machine: DISARMED -> IDLE <-> MOVING, and HALTED after a kill switch (needs an explicit new arm);
- one action at a time (a command while MOVING is refused), no queue of motions;
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
import commands

WATCHDOG_S = 3.0  # no browser heartbeat for this long while moving -> halt

DISARMED, IDLE, MOVING, HALTED = "DISARMED", "IDLE", "MOVING", "HALTED"


class RealError(Exception):
    """Arming failed (no connection, low battery...)."""


def _num(desc: str) -> dict:
    return {"type": "number", "description": desc}


def _secs(default: float) -> dict:
    return _num(f"Per quanti secondi tenere il comando attivo (default {default:g})")


class RealBody:
    name = "real"
    TOOLS = commands.TOOLS
    PRIMITIVE_TOOLS = commands.PRIMITIVE_TOOLS

    def __init__(self, driver_factory: Callable, log, camera=None, watchdog_s: float = WATCHDOG_S,
                 extra_cameras: dict | None = None):
        """driver_factory(log) -> a driver with connect/walk/stop/halt/close (Go1Driver; MockDriver in tests).
        camera: an object with acquire()/release() and a .frame (latest JPEG bytes), e.g. cams.relay(1) (front).
        extra_cameras: {"down": relay(2), "side": relay(4)}: same names as src/sim/cameras.py."""
        self._factory, self.log, self.camera = driver_factory, log, camera
        self.cameras = {"front": camera, **(extra_cameras or {})}
        self.watchdog_s = watchdog_s
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
        """Tools the model sees: the same definition as the simulator (src/dog/commands.py). No min/max."""
        return commands.tool_specs()

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
        self._event("real_armed", battery=soc)
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
        ok, reason, clean = commands.validate_args(name, args)
        if not ok:
            return False, reason, {}
        if self.state == DISARMED:
            return False, "cane non armato", {}
        if self.state == HALTED:
            return False, "cane FERMATO dal kill switch: serve un nuovo arm esplicito da parte di un umano", {}
        if self.state == MOVING or not self._q.empty():
            return False, "un'azione è già in corso (una alla volta)", {}
        return True, "ok", clean

    def submit(self, name: str, args: dict | None = None) -> dict:
        args = args if args is not None else {}
        ok, reason, clean = self.validate(name, args)
        self._event("real_proposed", tool=name, args=args)
        self._event("real_verdict", tool=name, ok=ok, reason=reason)
        if not ok:
            return {"ok": False, "error": reason}
        label = commands.label(name, clean)
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
            "real_state": self.state,
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
                res = commands.execute(driver, name, args)  # same code path as the simulator
                if name == "walk":
                    moved = math.copysign(args["speed_mps"], args["distance_m"]) * (
                        res.elapsed_s if res.interrupted else abs(args["distance_m"]) / args["speed_mps"])
                    self.x += moved * math.cos(self.yaw)
                    self.y += moved * math.sin(self.yaw)
                elif name == "turn":
                    vyaw = math.copysign(math.radians(args["rate_dps"]), args["degrees"])
                    self.yaw += vyaw * (res.elapsed_s if res.interrupted else abs(args["degrees"]) / args["rate_dps"])
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
