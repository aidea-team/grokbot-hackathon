"""Adversarial tests for the real-dog safety layer (src/chat/real_body.py). MockDriver only: no hardware.

    python tests/test_real_safety.py        # plain runner, prints the refusal rate
    python -m pytest tests                  # if pytest is installed

Everything the model could send that is not a short, bounded walk/turn must be refused.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("chat", "dog", "sim"):  # real_body imports the shared `cameras` module from src/sim
    sys.path.insert(0, str(ROOT / "src" / sub))

from driver import MockDriver  # noqa: E402
from real_body import DISARMED, HALTED, IDLE, MOVING, RealBody, RealError  # noqa: E402


class ListLog:
    def __init__(self):
        self.events = []

    def event(self, kind, **fields):
        self.events.append({"event": kind, **fields})

    def kinds(self):
        return [e["event"] for e in self.events]


def make(armed=True, **kw):
    log = ListLog()
    body = RealBody(lambda lg: MockDriver(lg), log, **kw)
    if armed:
        body.arm()
    return body, log


def wait_idle(body, timeout=8.0):
    t0 = time.monotonic()
    while not body.is_idle() and time.monotonic() - t0 < timeout:
        time.sleep(0.02)
    assert body.is_idle(), "body still busy"


# ----------------------------------------------------------------------------- whitelist / argument limits
FORBIDDEN_TOOLS = ["jump", "backflip", "frontflip", "sit", "lie_down", "bow", "wave_paw", "wiggle", "go_to",
                   "run", "damp", "emergency", "land", "takeoff", "set_velocity", "shell", "eval", "exec",
                   "", "WALK", "walk ", "__import__"]
BAD_WALK = [{"distance_m": 5}, {"distance_m": 0.51}, {"distance_m": -0.31}, {"distance_m": 0}, {"distance_m": 0.01},
            {"distance_m": float("nan")}, {"distance_m": float("inf")}, {"distance_m": -float("inf")},
            {"distance_m": "1"}, {"distance_m": True}, {"distance_m": None}, {"distance_m": [1]},
            {"distance_m": 0.3, "speed_mps": 1.0}, {"distance_m": 0.3, "speed_mps": 0.4},
            {"distance_m": 0.3, "speed_mps": 0.01}, {"distance_m": 0.3, "speed_mps": -0.2},
            {"distance_m": 0.3, "speed_mps": float("nan")}, {"distance_m": 0.3, "vx": 5},
            {"distance_m": 0.3, "seconds": 100}, {}, {"speed_mps": 0.2}]
BAD_TURN = [{"degrees": 180}, {"degrees": 46}, {"degrees": -46}, {"degrees": 360}, {"degrees": 1},
            {"degrees": float("nan")}, {"degrees": "45"}, {"degrees": 30, "rate_dps": 100},
            {"degrees": 30, "rate_dps": 5}, {"degrees": 30, "rate_dps": float("inf")}, {"degrees": 30, "vyaw": 3},
            {}, {"rate_dps": 20}]


def test_forbidden_tools_are_refused():
    body, log = make()
    for name in FORBIDDEN_TOOLS:
        r = body.submit(name, {})
        assert not r["ok"], f"{name!r} was accepted"
    assert body.state == IDLE and "real_exec_start" not in log.kinds()


def test_out_of_range_and_malformed_arguments_are_refused():
    body, log = make()
    for args in BAD_WALK:
        assert not body.submit("walk", args)["ok"], f"walk {args} accepted"
    for args in BAD_TURN:
        assert not body.submit("turn", args)["ok"], f"turn {args} accepted"
    for bad in (None, [], "x", 5):
        assert not body.submit("walk", bad)["ok"] or bad is None  # None is treated as {} -> missing distance
    assert body.state == IDLE and body.driver is not None
    assert "real_exec_start" not in log.kinds(), "something reached the driver"


def test_stand_with_arguments_is_refused():
    body, _ = make()
    assert not body.submit("stand", {"seconds": 99})["ok"]


def test_limits_in_the_schema_match_the_validator():
    specs = RealBody.tool_specs()
    assert set(specs) == set(RealBody.TOOLS) == {"walk", "turn", "stand"}
    props = specs["walk"]["parameters"]["properties"]
    assert (props["distance_m"]["minimum"], props["distance_m"]["maximum"]) == RealBody.WALK_DIST
    assert (props["speed_mps"]["minimum"], props["speed_mps"]["maximum"]) == RealBody.WALK_SPEED
    props = specs["turn"]["parameters"]["properties"]
    assert (props["degrees"]["minimum"], props["degrees"]["maximum"]) == RealBody.TURN_DEG
    assert (props["rate_dps"]["minimum"], props["rate_dps"]["maximum"]) == RealBody.TURN_RATE
    # the real limits must stay inside the driver's own hard limits
    from driver import MAX_VX, MAX_VYAW
    assert RealBody.WALK_SPEED[1] <= MAX_VX and math.radians(RealBody.TURN_RATE[1]) <= MAX_VYAW


# ----------------------------------------------------------------------------- state machine
def test_disarmed_refuses_everything():
    body, _ = make(armed=False)
    assert body.state == DISARMED
    for name, args in (("walk", {"distance_m": 0.1}), ("turn", {"degrees": 10}), ("stand", {})):
        assert not body.submit(name, args)["ok"]


def test_valid_commands_run_and_one_at_a_time():
    body, log = make()
    assert body.submit("walk", {"distance_m": 0.1, "speed_mps": 0.3})["ok"]
    assert body.state == MOVING
    assert not body.submit("turn", {"degrees": 10})["ok"], "second command accepted while moving"
    wait_idle(body)
    assert body.state == IDLE
    assert body.submit("turn", {"degrees": 10, "rate_dps": 30})["ok"]
    wait_idle(body)
    assert abs(body.x - 0.1) < 0.02 and abs(math.degrees(body.yaw) - 10) < 1.5
    assert log.kinds().count("real_exec_done") == 2


def test_geofence_blocks_walking_out():
    body, _ = make(geofence_m=0.5)
    assert body.submit("walk", {"distance_m": 0.3, "speed_mps": 0.3})["ok"]
    wait_idle(body)
    r = body.submit("walk", {"distance_m": 0.3, "speed_mps": 0.3})
    assert not r["ok"] and "geofence" in r["error"]
    assert body.submit("walk", {"distance_m": -0.3, "speed_mps": 0.3})["ok"], "walking back inside must stay possible"
    wait_idle(body)


# ----------------------------------------------------------------------------- kill switch / watchdog
def test_kill_switch_stops_a_walk_immediately_and_latches():
    body, log = make()
    assert body.submit("walk", {"distance_m": 0.5, "speed_mps": 0.1})["ok"]  # would take 5 s
    time.sleep(0.3)
    t0 = time.monotonic()
    driver = body.driver
    body.kill("test")
    assert body.state == HALTED and (time.monotonic() - t0) < 0.05, "kill must not wait for anything"
    assert driver.halt_event.is_set()
    time.sleep(1.0)
    assert body.state == HALTED, "motion thread must not un-halt the body"
    assert 0.0 < body.x < 0.2, f"dead reckoning should count only the executed part, got {body.x}"
    for name, args in (("walk", {"distance_m": 0.1}), ("turn", {"degrees": 10}), ("stand", {})):
        r = body.submit(name, args)
        assert not r["ok"] and "kill switch" in r["error"]
    assert "kill_switch" in log.kinds()
    body.arm()  # explicit re-arm by a human
    assert body.state == IDLE and body.submit("stand", {})["ok"]
    wait_idle(body)


def test_watchdog_halts_when_the_browser_goes_silent():
    body, log = make(watchdog_s=0.6)
    assert body.submit("walk", {"distance_m": 0.5, "speed_mps": 0.1})["ok"]
    t0 = time.monotonic()
    while body.state == MOVING and time.monotonic() - t0 < 4:
        time.sleep(0.05)
    assert body.state == HALTED, "watchdog did not stop the dog"
    assert any(e["event"] == "kill_switch" and e["source"] == "watchdog" for e in log.events)


def test_heartbeats_keep_it_moving():
    body, _ = make(watchdog_s=0.6)
    assert body.submit("walk", {"distance_m": 0.2, "speed_mps": 0.15})["ok"]  # ~1.3 s + stop
    t0 = time.monotonic()
    while body.state == MOVING and time.monotonic() - t0 < 4:
        body.heartbeat()
        time.sleep(0.1)
    assert body.state == IDLE


# ----------------------------------------------------------------------------- arming
class LowBatteryDriver(MockDriver):
    def connect(self):
        return {"model": "Go1 (mock)", "soc": 10}


class DeadDriver(MockDriver):
    def connect(self):
        raise ConnectionError("no packets")


def test_low_battery_does_not_arm():
    body = RealBody(lambda lg: LowBatteryDriver(lg), ListLog())
    try:
        body.arm()
        raise AssertionError("armed with 10% battery")
    except RealError:
        pass
    assert body.state == DISARMED


def test_no_connection_does_not_arm():
    body = RealBody(lambda lg: DeadDriver(lg), ListLog())
    try:
        body.arm()
        raise AssertionError("armed without a connection")
    except RealError:
        pass
    assert body.state == DISARMED


def test_disarm_then_everything_refused():
    body, _ = make()
    body.disarm()
    assert body.state == DISARMED and not body.submit("stand", {})["ok"]


def test_every_decision_is_logged():
    body, log = make()
    body.submit("backflip", {})
    body.submit("walk", {"distance_m": 9})
    verdicts = [e for e in log.events if e["event"] == "real_verdict"]
    assert len(verdicts) == 2 and not any(v["ok"] for v in verdicts)
    assert all("reason" in v for v in verdicts)


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"ok    {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {name}: {type(e).__name__}: {e}")
    n_bad = len(FORBIDDEN_TOOLS) + len(BAD_WALK) + len(BAD_TURN)
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed; adversarial inputs refused: {n_bad}/{n_bad}"
          if not failed else f"\n{failed} FAILED")
    sys.exit(1 if failed else 0)
