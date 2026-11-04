"""BothBody: the chat drives the real Go1 AND the simulator with the very same commands.

The real dog is the source of truth (its safety layer, state machine and kill switch decide); the simulator is a
mirror that receives exactly what the real dog received. Rules:
- a command goes to the real dog first (validation, ARMED/HALTED state, one-at-a-time all live there); if the real
  dog refuses, NOTHING is sent to the simulator, so the two never diverge on a refusal;
- the agent sees the REAL cameras and the real (estimated) odometry; the simulator's pose is reported next to it
  ("sim") so a human can compare the two bodies;
- STOP acts on both. Nothing here adds or removes a limit: it only forwards.
"""
from __future__ import annotations


class BothBody:
    name = "both"

    def __init__(self, sim, real):
        self.sim, self.real = sim, real

    # ---- the agent-facing interface (same as RealBody / SimBody)
    def submit(self, name: str, args: dict | None = None) -> dict:
        r = self.real.submit(name, args)
        if not r["ok"]:
            return r  # refused by the real dog: the simulator does not get it either
        s = self.sim.submit(name, args)
        if not s["ok"]:  # same validation as the real one, so this should never happen: surface it
            r = {**r, "sim_error": s.get("error", "refused")}
        return r

    def is_idle(self) -> bool:
        return self.real.is_idle() and self.sim.is_idle()

    def clear(self) -> None:
        self.real.clear()
        self.sim.clear()

    def capture(self, width: int = 512, height: int = 384, camera: str = "front",
                wait_idle: bool = False, timeout: float = 120.0) -> bytes | None:
        return self.real.capture(width, height, camera, wait_idle, timeout)

    def reset_pose(self) -> None:
        self.real.reset_pose()  # only zeroes the real dog's odometry origin
        self.sim.reset_pose()

    def set_time_scale(self, scale: float) -> None:
        pass  # both must run at real time to stay comparable

    def snapshot(self) -> dict:
        snap = self.real.snapshot()
        s = self.sim.snapshot()
        snap["sim"] = {k: s.get(k) for k in ("x", "y", "yaw_deg", "z", "posture", "current")}
        return snap

    # feedback flags: the real dog's (it has none); the simulator's contact feedback would describe another world
    @property
    def last_block(self):
        return self.real.last_block

    @property
    def last_stuck(self):
        return self.real.last_stuck

    @property
    def last_crash(self):
        return self.real.last_crash

    @property
    def last_fell(self):
        return self.real.last_fell
