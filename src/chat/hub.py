"""RobotHub: which body the chat drives, the MuJoCo simulator or the real Go1.

The default is always the simulator. The real dog is available only if the app was launched by a human with
`--real` and the human typed `go` at the terminal (see app.py): that makes `real` non-None. Even then, switching
to it needs an explicit confirmation from the browser (the arm click), which connects to the dog, checks the
battery and enters IDLE. Switching back to the simulator disarms the dog.
"""
from __future__ import annotations

import threading

from real_body import DISARMED, RealBody, RealError


class HubError(Exception):
    """Mode switch refused; the message is shown to the human."""


class RobotHub:
    def __init__(self, sim, real: RealBody | None = None, log=None):
        self.sim, self.real, self.log = sim, real, log
        self.mode = "sim"
        self._lock = threading.Lock()

    @property
    def real_enabled(self) -> bool:
        return self.real is not None

    @property
    def body(self):
        return self.real if (self.mode == "real" and self.real is not None) else self.sim

    def set_mode(self, mode: str, confirm: bool = False) -> dict:
        with self._lock:
            if mode == "sim":
                if self.real is not None:
                    self.real.disarm()
                self.mode = "sim"
            elif mode == "real":
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
                self.mode = "real"
            else:
                raise HubError(f"modalità sconosciuta: {mode!r}")
        self._event("mode_switch", mode=self.mode)
        return self.status()

    def kill(self, source: str) -> None:
        """Stop whatever is being driven. On the real dog it latches HALTED until a human re-arms."""
        if self.mode == "real" and self.real is not None:
            self.real.kill(source)
        else:
            self.sim.clear()

    def heartbeat(self) -> None:
        if self.real is not None:
            self.real.heartbeat()

    def status(self) -> dict:
        real_state = self.real.state if self.real is not None else None
        return {
            "mode": self.mode, "real_enabled": self.real_enabled, "real_state": real_state,
            "armed": real_state not in (None, DISARMED) and self.mode == "real",
            "battery": self.real.battery if self.real is not None else None,
            "geofence_m": self.real.geofence_m if self.real is not None else None,
        }

    def _event(self, kind: str, **fields) -> None:
        if self.log is not None:
            self.log.event(kind, **fields)
