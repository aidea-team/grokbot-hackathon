"""SimDriver: the Go1 driver interface (walk / drive / primitive / stop / halt) backed by the MuJoCo world.

It plays the role of Go1Driver. commands.execute() calls it exactly like it calls the real driver; what leaves it is
what Go1Driver would put on the UDP link: a velocity (vx, vyaw) or a high-level MODE (src/dog/driver.py PRIMITIVES).
The world (dog_world.DogSim) interprets those like the firmware would. Time is SIMULATED time, so slow-motion and
fast-forward do not change what a command means.
"""
from __future__ import annotations

from driver import JsonlLog, _BaseDriver


class SimDriver(_BaseDriver):
    name = "sim"

    def __init__(self, world, log: JsonlLog | None = None):
        super().__init__(log if log is not None else _NullLog())
        self.world = world

    def connect(self) -> dict:
        return {"model": "Go1 (MuJoCo)", "soc": 100}

    def now(self) -> float:
        return self.world.sim_time

    def sleep(self, seconds: float) -> None:
        self.world.wait_sim_time(seconds)

    def _send_velocity(self, vx: float, vyaw: float) -> None:
        self.world.set_command(vx=vx, vyaw=vyaw, mode="VEL_WALK")

    def _send_idle(self) -> None:
        self.world.set_command(vx=0.0, vyaw=0.0, mode="IDLE")

    def _send_mode(self, mode: str) -> None:
        self.world.set_command(vx=0.0, vyaw=0.0, mode=mode)

    def close(self) -> None:
        self._send_idle()


class _NullLog:
    def event(self, kind: str, **fields) -> None:
        pass
