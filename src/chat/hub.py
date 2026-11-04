"""RobotHub: which robot (Go1 | Go2) and which body the chat drives (mock/simulator or the real dog).

Robot Go1: the MuJoCo simulator or the real Go1 (or both together). Robot Go2: a mock (kinematic, no physics; a
RealBody over Go2MockDriver) or the real Go2 over WebRTC. The Go2 has no `both` mode (no physical simulator for it).

The default is always the simulator. The real dog is available only if the app was launched by a human with
`--real` and the human typed `go` at the terminal (see app.py): that makes `real` non-None. Even then, switching
to it needs an explicit confirmation from the browser (the arm click), which connects to the dog, checks the
battery and enters IDLE. Switching back to the simulator disarms the dog.
"""
from __future__ import annotations

import math
import threading
import time

from both_body import BothBody
from real_body import DISARMED, RealBody, RealError


class HubError(Exception):
    """Mode switch refused; the message is shown to the human."""


class RobotHub:
    def __init__(self, sim, real: RealBody | None = None, log=None,
                 go2_sim: RealBody | None = None, go2_real: RealBody | None = None):
        self.sim, self.real, self.log = sim, real, log
        self.go2_sim, self.go2_real = go2_sim, go2_real
        self.robot = "go1"  # "go1" | "go2"
        self._both = BothBody(sim, real) if real is not None else None
        self._tele = (0.0, 0.0, 0.0)
        self._tele_lock = threading.Lock()
        self._tele_thread: threading.Thread | None = None
        self.mode = "sim"  # "sim" | "real" | "both" (the same commands to the real dog and to the simulator)
        self._lock = threading.Lock()

    @property
    def active_sim(self):
        """The mock/simulator body of the selected robot."""
        return self.go2_sim if self.robot == "go2" else self.sim

    @property
    def active_real(self) -> RealBody | None:
        """The real-dog body of the selected robot (None if the app was not launched with --real)."""
        return self.go2_real if self.robot == "go2" else self.real

    @property
    def real_enabled(self) -> bool:
        return self.active_real is not None

    @property
    def body(self):
        if self.robot == "go2":
            return self.go2_real if (self.mode == "real" and self.go2_real is not None) else self.go2_sim
        if self.mode == "both" and self._both is not None:
            return self._both
        return self.real if (self.mode == "real" and self.real is not None) else self.sim

    @property
    def robots(self) -> list[str]:
        return ["go1", "go2"] if self.go2_sim is not None else ["go1"]

    def set_robot(self, robot: str) -> dict:
        """Go1 <-> Go2. Always returns to the safe mock/simulator body of the new robot (the real dog of the robot we
        leave is disarmed); the caller aborts the running mission and resets the conversation."""
        with self._lock:
            if robot not in ("go1", "go2"):
                raise HubError(f"robot sconosciuto: {robot!r}")
            if robot == "go2" and self.go2_sim is None:
                raise HubError("Il Go2 non è disponibile in questa istanza.")
            if robot != self.robot:
                if self.active_real is not None:
                    self.active_real.disarm()
                if self.robot == "go2":
                    self.go2_sim.disarm()
                self.robot, self.mode = robot, "sim"
                if robot == "go2":
                    self._arm_mock()
        self._event("robot_switch", robot=self.robot)
        return self.status()

    def _arm_mock(self) -> None:
        try:
            self.go2_sim.arm()  # the mock Go2 has no hardware: arming cannot fail for real reasons
        except RealError as e:
            raise HubError(str(e)) from e

    @property
    def real_like(self) -> bool:
        """True when the real dog is being driven (alone or together with the simulator)."""
        return self.mode in ("real", "both")

    def set_mode(self, mode: str, confirm: bool = False) -> dict:
        with self._lock:
            if self.robot == "go2":
                self._set_mode_go2(mode, confirm)
            elif mode == "sim":
                if self.real is not None:
                    self.real.disarm()
                self.mode = "sim"
            elif mode in ("real", "both"):
                if self.real is None:
                    raise HubError("Il cane vero non è abilitato. Una persona deve avviare l'app dal terminale con "
                                   "`--real` (e scrivere «go» per armare). Resto sul simulatore.")
                if not confirm:
                    raise HubError("Serve la conferma esplicita (checklist) per passare al cane vero.")
                try:
                    self.real.arm()
                except RealError as e:
                    self.mode = "sim"
                    raise HubError(str(e)) from e
                if mode == "both":  # the mirror starts where the real dog starts (origin) and runs at real time
                    self.sim.set_time_scale(1.0)
                    self.sim.reset_pose()
                self.mode = mode
            else:
                raise HubError(f"modalità sconosciuta: {mode!r}")
        self._event("mode_switch", mode=self.mode)
        return self.status()

    def _set_mode_go2(self, mode: str, confirm: bool) -> None:
        if mode == "sim":
            if self.go2_real is not None:
                self.go2_real.disarm()
            self.mode = "sim"
            self._arm_mock()  # usable again even if the mock was halted
        elif mode == "real":
            if self.go2_real is None:
                raise HubError("Il Go2 vero non è abilitato. Una persona deve avviare l'app dal terminale con "
                               "`--real` (e scrivere «go» per armare). Resto sul mock.")
            if not confirm:
                raise HubError("Serve la conferma esplicita (checklist) per passare al Go2 vero.")
            try:
                self.go2_real.arm()
            except RealError as e:
                self.mode = "sim"
                raise HubError(str(e)) from e
            self.mode = "real"
        elif mode == "both":
            raise HubError("La modalità both esiste solo per il Go1: per il Go2 non c'è un simulatore fisico.")
        else:
            raise HubError(f"modalità sconosciuta: {mode!r}")

    # ------------------------------------------------------------------ manual driving (WASD)
    TELEOP_DT = 0.02  # s between velocity ticks
    TELEOP_FRESH_S = 0.4  # no update from the browser for this long -> stop (watchdog)

    def teleop(self, fwd: float, turn: float, speed: float, rate_dps: float) -> None:
        """Set the manual target: fwd, turn in {-1, 0, 1}; speed m/s, rate deg/s. Called repeatedly while keys are held."""
        with self._tele_lock:
            self._tele = (fwd * abs(speed), turn * math.radians(abs(rate_dps)), time.monotonic())
            if self._tele_thread is None or not self._tele_thread.is_alive():
                self._tele_thread = threading.Thread(target=self._teleop_loop, daemon=True, name="teleop")
                self._tele_thread.start()

    def _teleop_loop(self) -> None:
        active = False
        while True:
            time.sleep(self.TELEOP_DT)
            with self._tele_lock:
                vx, vyaw, t = self._tele
            fresh = time.monotonic() - t < self.TELEOP_FRESH_S
            if not fresh or (vx == 0.0 and vyaw == 0.0):
                vx = vyaw = 0.0
            body = self.body
            if not hasattr(body, "teleop_tick"):
                continue
            if vx or vyaw:
                active = body.teleop_tick(vx, vyaw, self.TELEOP_DT)
            elif active:
                body.teleop_tick(0.0, 0.0, self.TELEOP_DT)  # back to idle once
                active = False

    def kill(self, source: str) -> None:
        """Stop whatever is being driven. On the real dog it latches HALTED until a human re-arms."""
        if self.robot == "go2":
            if self.mode == "real" and self.go2_real is not None:
                self.go2_real.kill(source)
            else:
                self.go2_sim.kill(source)
                self._arm_mock()  # the mock has nothing to protect: the Stop button must not leave it latched
        elif self.real_like and self.real is not None:
            self.real.kill(source)
            if self.mode == "both":
                self.sim.clear()
        else:
            self.sim.clear()

    def heartbeat(self) -> None:
        for body in (self.real, self.go2_sim, self.go2_real):
            if body is not None:
                body.heartbeat()

    def status(self) -> dict:
        real = self.active_real
        real_state = real.state if real is not None else None
        return {
            "mode": self.mode, "real_enabled": self.real_enabled, "real_state": real_state,
            "armed": real_state not in (None, DISARMED) and self.real_like,
            "battery": real.battery if real is not None else None,
            "robot": self.robot, "robots": self.robots,
        }

    def _event(self, kind: str, **fields) -> None:
        if self.log is not None:
            self.log.event(kind, **fields)
