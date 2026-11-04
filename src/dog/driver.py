"""Unitree Go1 drivers with one shared interface.

- MockDriver (default): no network, integrates a 2D pose, same timing as the real dog.
- Go1Driver: high-level commands over UDP via free-dog-sdk (vendor/free-dog-sdk, see
  scripts/setup.sh). Works on Go1 Air/Pro/Edu connected to the dog's Wi-Fi hotspot.

NO numeric limits here on purpose (2026-11-04): velocities, durations and the Go1 high-level modes (dance,
jumpYaw, backflip, damping...) all go through. The guardrails are being rewritten by the team: until then
only sanity checks (finite numbers, positive duration) and the halt() kill switch exist at this level.
"""
from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Go1 high-level "primitives" (MotorModeHigh) and how long we keep sending the mode. DURATIONS ARE ESTIMATES,
# not verified on the dog (nobody has run them yet): the dog finishes the move on its own, we only keep the
# mode on the wire. Adjust at the first human-supervised test.
PRIMITIVES: dict[str, tuple[str, float]] = {
    "stand_up": ("STAND_UP", 2.0),
    "lie_down": ("STAND_DOWN", 3.0),
    "recovery": ("RECOVERY", 4.0),
    "backflip": ("BACKFLIP", 4.0),
    "jump_yaw": ("JUMPYAW", 4.0),
    "straight_hand": ("STRAIGHTHAND", 4.0),
    "dance1": ("DANCE1", 15.0),
    "dance2": ("DANCE2", 15.0),
    "damping": ("DAMPING", 2.0),
}
LOOP_DT = 0.002  # 500 Hz, as in free-dog-sdk examples
STOP_S = 0.5  # how long we keep sending zero velocity when stopping


class JsonlLog:
    """Append-only JSONL event log (logs/ is gitignored)."""

    def __init__(self, path: Path | None = None):
        path = path or REPO_ROOT / "logs" / f"dog-{time.strftime('%Y%m%d')}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()

    def event(self, kind: str, **fields) -> None:
        rec = {"ts": round(time.time(), 3), "event": kind, **fields}
        with self._lock, self.path.open("a") as f:
            f.write(json.dumps(rec) + "\n")


def validate_walk(vx: float, vyaw: float, seconds: float) -> tuple[bool, str]:
    if not all(math.isfinite(v) for v in (vx, vyaw, seconds)):
        return False, "non-finite argument"
    if seconds <= 0:
        return False, f"seconds={seconds} must be > 0"
    return True, "ok"


@dataclass
class WalkResult:
    ok: bool
    reason: str
    elapsed_s: float = 0.0
    interrupted: bool = False


class _BaseDriver:
    name = "base"
    LOOP_DT = LOOP_DT  # seconds between two commands on the wire (a subclass may slow this down: Go2 uses WebRTC)
    STOP_S = STOP_S

    def __init__(self, log: JsonlLog):
        self.log = log
        self.halt_event = threading.Event()  # set by the kill switch, never cleared mid-walk

    def halt(self) -> None:
        """Kill switch entry point: lock-free, callable from any thread."""
        self.halt_event.set()

    # Clock hooks: wall time for the dog, simulated time for SimDriver (so slow-mo / fast-forward stay consistent).
    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def walk(self, vx: float, vyaw: float, seconds: float) -> WalkResult:
        ok, reason = validate_walk(vx, vyaw, seconds)
        self.log.event("walk_request", driver=self.name, vx=vx, vyaw=vyaw, seconds=seconds,
                       verdict=ok, reason=reason)
        if not ok:
            return WalkResult(False, reason)
        if self.halt_event.is_set():
            return WalkResult(False, "halted")
        t0 = self.now()
        try:
            while (elapsed := self.now() - t0) < seconds:
                if self.halt_event.is_set():
                    break
                self._send_velocity(vx, vyaw)
                self.sleep(self.LOOP_DT)
        finally:
            self.stop()
        elapsed = self.now() - t0
        interrupted = self.halt_event.is_set()
        self.log.event("walk_done", driver=self.name, elapsed_s=round(elapsed, 3),
                       interrupted=interrupted)
        return WalkResult(not interrupted, "halted" if interrupted else "ok",
                          round(elapsed, 3), interrupted)

    def primitive(self, name: str, seconds: float | None = None) -> WalkResult:
        """Run one of PRIMITIVES: keep sending its mode for `seconds` (default from PRIMITIVES), then idle.
        halt() interrupts it like a walk."""
        if name not in PRIMITIVES:
            return WalkResult(False, f"unknown primitive {name!r}")
        mode, default_s = PRIMITIVES[name]
        seconds = default_s if seconds is None else seconds
        if not math.isfinite(seconds) or seconds <= 0:
            return WalkResult(False, f"seconds={seconds} must be a finite number > 0")
        self.log.event("primitive_request", driver=self.name, primitive=name, mode=mode, seconds=seconds)
        if self.halt_event.is_set():
            return WalkResult(False, "halted")
        t0 = self.now()
        try:
            while self.now() - t0 < seconds:
                if self.halt_event.is_set():
                    break
                self._send_mode(mode)
                self.sleep(self.LOOP_DT)
        finally:
            self.stop()
        elapsed = self.now() - t0
        interrupted = self.halt_event.is_set()
        self.log.event("primitive_done", driver=self.name, primitive=name, elapsed_s=round(elapsed, 3),
                       interrupted=interrupted)
        return WalkResult(not interrupted, "halted" if interrupted else "ok", round(elapsed, 3), interrupted)

    def drive(self, vx: float, vyaw: float) -> bool:
        """One teleop tick: validated velocity (or idle when both are 0). Caller loops and owns the
        watchdog. Returns False if refused (invalid or halted); then idle is sent."""
        ok, _ = validate_walk(vx, vyaw, 1.0)
        if not ok or self.halt_event.is_set():
            self._send_idle()
            return False
        if vx == 0.0 and vyaw == 0.0:
            self._send_idle()
        else:
            self._send_velocity(vx, vyaw)
        return True

    def stop(self) -> None:
        t0 = self.now()
        while self.now() - t0 < self.STOP_S:
            self._send_idle()
            self.sleep(self.LOOP_DT)
        self.log.event("stop", driver=self.name)

    # implemented by subclasses
    def connect(self) -> dict: ...
    def close(self) -> None: ...
    def _send_velocity(self, vx: float, vyaw: float) -> None: ...
    def _send_idle(self) -> None: ...
    def _send_mode(self, mode: str) -> None: ...


class MockDriver(_BaseDriver):
    name = "mock"

    def __init__(self, log: JsonlLog):
        super().__init__(log)
        self.x = self.y = self.yaw = 0.0
        self._last = time.monotonic()

    def connect(self) -> dict:
        info = {"model": "Go1 (mock)", "soc": 100}
        self.log.event("connect", driver=self.name, **info)
        return info

    def _integrate(self, vx: float, vyaw: float) -> None:
        now = time.monotonic()
        dt, self._last = now - self._last, now
        self.yaw += vyaw * dt
        self.x += vx * math.cos(self.yaw) * dt
        self.y += vx * math.sin(self.yaw) * dt

    def _send_velocity(self, vx: float, vyaw: float) -> None:
        self._integrate(vx, vyaw)

    def _send_idle(self) -> None:
        self._integrate(0.0, 0.0)

    def _send_mode(self, mode: str) -> None:
        self._integrate(0.0, 0.0)

    def pose(self) -> dict:
        return {"x": round(self.x, 3), "y": round(self.y, 3), "yaw": round(self.yaw, 3)}

    def close(self) -> None:
        self.log.event("close", driver=self.name, pose=self.pose())


class Go1Driver(_BaseDriver):
    name = "go1"

    def __init__(self, log: JsonlLog, addr: str | None = None):
        super().__init__(log)
        try:
            from ucl.enums import GaitType, MotorModeHigh
            from ucl.highCmd import highCmd
            from ucl.highState import highState
            from ucl.unitreeConnection import unitreeConnection
        except ImportError:  # venv without the .pth from scripts/setup.sh
            sys.path.insert(0, str(REPO_ROOT / "vendor" / "free-dog-sdk"))
            try:
                from ucl.enums import GaitType, MotorModeHigh
                from ucl.highCmd import highCmd
                from ucl.highState import highState
                from ucl.unitreeConnection import unitreeConnection
            except ImportError as e:
                raise SystemExit("free-dog-sdk not found: run ./scripts/setup.sh") from e
        self._Mode, self._Gait = MotorModeHigh, GaitType
        self._highState = highState
        self.addr = addr or os.environ.get("GO1_ADDR", "192.168.12.1")
        # (listenPort, dog ip, dog high-level port, local ip); local ip/port unused by the lib
        self.conn = unitreeConnection((8090, self.addr, 8082, "0.0.0.0"))
        self.cmd = highCmd()

    def connect(self) -> dict:
        self.conn.startRecv()
        self.conn.send(self.cmd.buildCmd())  # empty cmd: tells the dog where to answer
        time.sleep(0.5)
        packets = self.conn.getData()
        if not packets:
            self.log.event("connect_failed", driver=self.name, addr=self.addr)
            raise ConnectionError(
                f"no packets from {self.addr}: are you on the dog's Wi-Fi? try `ping {self.addr}`")
        st = self._highState()
        st.parseData(packets[-1])
        info = {"addr": self.addr, "soc": st.bms.SOC, "packets": len(packets)}
        self.log.event("connect", driver=self.name, **info)
        return info

    def _send_velocity(self, vx: float, vyaw: float) -> None:
        c = self.cmd
        c.mode = self._Mode.VEL_WALK
        c.gaitType = self._Gait.TROT
        c.velocity = [vx, 0.0]
        c.yawSpeed = vyaw
        self.conn.send(c.buildCmd())

    def _send_idle(self) -> None:
        c = self.cmd
        c.mode = self._Mode.IDLE  # stand still (NOT DAMPING: that would drop the dog)
        c.gaitType = self._Gait.IDLE
        c.velocity = [0.0, 0.0]
        c.yawSpeed = 0.0
        self.conn.send(c.buildCmd())

    def _send_mode(self, mode: str) -> None:
        c = self.cmd
        c.mode = getattr(self._Mode, mode)
        c.gaitType = self._Gait.IDLE
        c.velocity = [0.0, 0.0]
        c.yawSpeed = 0.0
        self.conn.send(c.buildCmd())

    def close(self) -> None:
        self.stop()
        self.conn.stopRecv()
        self.log.event("close", driver=self.name)
