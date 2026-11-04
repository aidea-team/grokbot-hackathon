"""The two bodies of the Go2: a mock for trying everything without hardware, and the real dog over WebRTC.

Both are a `RealBody` (same state machine, kill switch, watchdog and JSONL log as the Go1) with the Go2 command set
(src/dog/go2_commands.py) over a Go2 driver. The mock is armed by the hub when the Go2 is selected; the real one only
exists when the app was launched by a human with `--real`, and connects (WebRTC) only after the arm click.
"""
from __future__ import annotations

from real_body import RealBody
import go2_commands
from go2_driver import Go2Driver, Go2Link, Go2MockDriver, MockTopCamera


def make_go2_mock(log) -> RealBody:
    holder: dict = {}

    def factory(lg):
        holder["driver"] = Go2MockDriver(lg)
        return holder["driver"]

    return RealBody(factory, log, camera=MockTopCamera(lambda: holder.get("driver")),
                    cmds=go2_commands, robot="go2")


def make_go2_real(log, link: Go2Link | None = None) -> tuple[RealBody, Go2Link]:
    link = link or Go2Link()
    body = RealBody(lambda lg: Go2Driver(lg, link), log, camera=link.camera, cmds=go2_commands, robot="go2")
    return body, link
