"""SimBody: the simulated dog as the chat agent sees it, same interface as RealBody.

Commands go through the SAME code as the real dog (commands.validate_args / commands.execute) into a SimDriver, so the
simulator receives exactly the velocities and Go1 modes the real dog would. There is no safety state machine here (a
virtual world): STOP aborts the running command and the dog holds still (IDLE).

On top of that it reports PHYSICAL FEEDBACK that the real dog does not give (which prop was touched, stuck, fell,
crashed): diagnostics read from the contacts, never commands.
"""
from __future__ import annotations

import math
import queue
import threading

import commands
from sim_driver import SimDriver


class SimBody:
    name = "sim"

    def __init__(self, world, log=None):
        self.world, self.log = world, log
        self.driver = SimDriver(world, log)
        self._q: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._current: str | None = None
        self._pending: list[str] = []
        self._done = 0
        self._abort = threading.Event()
        self._quit = threading.Event()
        self.last_block: str | None = None
        self.last_stuck = self.last_crash = self.last_fell = False
        self._thread = threading.Thread(target=self._worker, daemon=True, name="sim-worker")
        self._thread.start()

    # ------------------------------------------------------------------ agent-facing interface (same as RealBody)
    @property
    def jpeg_quality(self) -> int:
        return self.world.jpeg_quality

    @jpeg_quality.setter
    def jpeg_quality(self, value: int) -> None:
        self.world.jpeg_quality = value

    def submit(self, name: str, args: dict | None = None) -> dict:
        ok, reason, clean = commands.validate_args(name, args)
        if not ok:
            self._event("sim_command_refused", command=name, reason=reason)
            return {"ok": False, "error": reason}
        label = commands.label(name, clean)
        with self._lock:
            self._pending.append(label)
        self._q.put((name, clean, label))
        self._event("sim_command_queued", command=label)
        return {"ok": True, "queued": label, "queue_length": self._q.qsize() + (1 if self._current else 0)}

    def is_idle(self) -> bool:
        with self._lock:
            return self._current is None and self._q.empty() and not self._pending

    def teleop_tick(self, vx: float, vyaw: float, dt: float) -> bool:
        """Manual (WASD) driving: one velocity tick straight to the driver, like the real dog. Refused while a
        command is running (one thing at a time)."""
        if not self.is_idle():
            return False
        return self.driver.drive(vx, vyaw)

    def clear(self) -> None:
        """STOP: drop the queue, abort the running command; the dog holds still."""
        while not self._q.empty():
            try:
                self._q.get_nowait()
            except queue.Empty:
                break
        with self._lock:
            running = self._current
            self._pending = [running] if running else []
        if running:  # nothing to abort when idle: a latched halt would refuse the next command
            self._abort.set()
            self.driver.halt()

    def capture(self, width: int = 512, height: int = 384, camera: str = "front",
                wait_idle: bool = False, timeout: float = 120.0) -> bytes | None:
        if wait_idle:
            import time
            deadline = time.monotonic() + timeout
            while not self.is_idle() and time.monotonic() < deadline:
                time.sleep(0.1)
        return self.world.capture(width, height, camera)

    def reset_pose(self) -> None:
        self.clear()
        self.world.reset_pose()

    def set_time_scale(self, scale: float) -> None:
        self.world.set_time_scale(scale)

    def snapshot(self) -> dict:
        snap = self.world.snapshot()
        with self._lock:
            pending = list(self._pending)
            snap.update(current=self._current, queue=pending[1:] if self._current else pending, done=self._done)
        return snap

    def shutdown(self) -> None:
        self._quit.set()
        self.driver.halt()

    # ------------------------------------------------------------------ worker
    def _worker(self) -> None:
        while not self._quit.is_set():
            try:
                name, clean, label = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            with self._lock:
                self._current = label
            w = self.world
            x0, y0, yaw0 = w.x, w.y, w.yaw
            w.begin_command()
            self._event("sim_command_start", command=label)
            try:
                res = commands.execute(self.driver, name, clean)
            except Exception as e:  # noqa: BLE001 - a broken command must not kill the worker
                self._event("sim_command_error", command=label, error=repr(e))
                res = None
            if self._abort.is_set() or self.driver.halt_event.is_set():  # STOP: walk()/primitive() already went IDLE
                self._abort.clear()
                self.driver.halt_event.clear()
            self._diagnose(name, clean, x0, y0, yaw0)
            self._event("sim_command_done", command=label, ok=bool(res.ok) if res else True,
                        touched=sorted(w.touched_action), stuck=self.last_stuck, crashed=self.last_crash,
                        fell=self.last_fell)
            with self._lock:
                self._done += 1
                if label in self._pending:
                    self._pending.remove(label)
                self._current = None

    def _diagnose(self, name: str, clean: dict, x0: float, y0: float, yaw0: float) -> None:
        """Physical feedback for the agent (NOT available on the real dog): what was touched, blocked, fell."""
        w = self.world
        touched = sorted(w.touched_action)
        self.last_block = touched[0] if touched else None
        self.last_crash = bool(w.crashed)
        self.last_fell = w.tilt() > 0.9
        self.last_stuck = False
        if name == "walk" and touched:  # blocked: it walked much less than commanded and touched something
            moved = abs((w.x - x0) * math.cos(yaw0) + (w.y - y0) * math.sin(yaw0))
            self.last_stuck = moved < 0.5 * abs(clean["distance_m"])

    def _event(self, kind: str, **fields) -> None:
        if self.log is not None:
            try:
                self.log.event(kind, **fields)
            except Exception:  # noqa: BLE001
                pass
