"""The chat app's mock/real switch, through the HTTP API. MockDriver only: the real dog is never reachable here.

    python tests/test_chat_modes.py
"""
from __future__ import annotations

import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("chat", "dog", "sim"):
    sys.path.insert(0, str(ROOT / "src" / sub))

from fastapi.testclient import TestClient  # noqa: E402

from app import create_app  # noqa: E402
from dog_agent import DogAgent  # noqa: E402
from dog_world import DogSim  # noqa: E402
from sim_body import SimBody  # noqa: E402
from driver import MockDriver  # noqa: E402
from hub import RobotHub  # noqa: E402
from real_body import RealBody  # noqa: E402


class FakeCam:
    frame = b"\xff\xd8fake\xff\xd9"

    def acquire(self): pass
    def release(self): pass


class ListLog:
    def __init__(self):
        self.events = []
        self.path = Path(tempfile.mkdtemp()) / "log.jsonl"  # DogAgent keeps its settings.json next to the log
    def event(self, kind, **f): self.events.append({"event": kind, **f})


def build(real_enabled: bool):
    log = ListLog()
    sim = SimBody(DogSim(headless=True, log=log), log)
    real = RealBody(lambda lg: MockDriver(lg), log, camera=FakeCam()) if real_enabled else None
    hub = RobotHub(sim, real, log)
    return TestClient(create_app(hub, sim, DogAgent(hub, log))), hub, log


def test_real_is_refused_when_not_launched_with_real():
    client, hub, _ = build(real_enabled=False)
    r = client.post("/api/mode", json={"mode": "real", "confirm": True}).json()
    assert not r["ok"] and "--real" in r["error"] and r["mode"] == "sim"
    assert client.get("/cam/1.mjpg").status_code == 404, "real cameras must not be reachable without --real"
    assert client.get("/api/state").json()["real_enabled"] is False


def test_real_needs_explicit_confirm_then_arms_and_switches_back():
    client, hub, log = build(real_enabled=True)
    r = client.post("/api/mode", json={"mode": "real"}).json()  # no confirm
    assert not r["ok"] and hub.mode == "sim" and hub.real.state == "DISARMED"
    r = client.post("/api/mode", json={"mode": "real", "confirm": True}).json()
    assert r["ok"] and r["mode"] == "real" and r["real_state"] == "IDLE" and r["armed"]
    s = client.get("/api/state").json()
    assert s["mode"] == "real" and s["estimated"] is True and s["real_state"] == "IDLE"
    r = client.post("/api/mode", json={"mode": "sim"}).json()
    assert r["ok"] and r["mode"] == "sim" and r["real_state"] == "DISARMED" and not r["armed"]


def test_stop_in_real_mode_latches_halted_until_rearm():
    client, hub, _ = build(real_enabled=True)
    client.post("/api/mode", json={"mode": "real", "confirm": True})
    assert hub.body.submit("walk", {"distance_m": 0.5, "speed_mps": 0.1})["ok"]
    time.sleep(0.2)
    r = client.post("/api/stop").json()
    assert r["real_state"] == "HALTED"
    time.sleep(0.8)
    assert hub.real.state == "HALTED" and not hub.body.submit("stand", {})["ok"]
    r = client.post("/api/mode", json={"mode": "real", "confirm": True}).json()  # explicit re-arm
    assert r["ok"] and r["real_state"] == "IDLE"


def test_agent_tools_in_real_mode_are_all_the_go1_primitives_without_limits():
    from dog_agent import build_tools
    names = [t["name"] for t in build_tools("real")]
    assert names[-1] == "finish" and set(names[:-1]) == set(RealBody.TOOLS)
    for t in build_tools("real"):
        for prop in t["parameters"]["properties"].values():
            assert "minimum" not in prop and "maximum" not in prop, "numeric limits must not be in the schema"


def _step_world(hub):
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            hub.sim.world.step(1 / 60)
            time.sleep(0.0005)
    threading.Thread(target=loop, daemon=True).start()
    return stop


def _spy(body, seen):
    orig = body.submit

    def submit(name, args=None):
        r = orig(name, args)
        seen.append((name, dict(args or {}), r["ok"]))
        return r
    body.submit = submit


def test_both_mode_sends_the_same_command_to_the_real_dog_and_the_simulator():
    client, hub, _ = build(real_enabled=True)
    stop = _step_world(hub)
    try:
        r = client.post("/api/mode", json={"mode": "both"}).json()  # needs the explicit confirm like real
        assert not r["ok"] and hub.mode == "sim"
        r = client.post("/api/mode", json={"mode": "both", "confirm": True}).json()
        assert r["ok"] and r["mode"] == "both" and r["armed"] and r["real_state"] == "IDLE"
        real_seen, sim_seen = [], []
        _spy(hub.real, real_seen)
        _spy(hub.sim, sim_seen)
        assert hub.body.submit("walk", {"distance_m": 0.1, "speed_mps": 0.2})["ok"]
        t0 = time.monotonic()
        while not hub.body.is_idle() and time.monotonic() - t0 < 30:
            time.sleep(0.02)
        assert hub.body.is_idle()
        assert real_seen == sim_seen == [("walk", {"distance_m": 0.1, "speed_mps": 0.2}, True)]
        s = client.get("/api/state").json()
        assert s["mode"] == "both" and s["estimated"] is True and "sim" in s
        assert abs(s["x"] - 0.1) < 0.03, "the real (mock) dog moved"
        assert s["sim"]["x"] > 0.03, "the simulator moved too"
        # a command the real dog refuses must not reach the simulator
        assert not hub.body.submit("walk", {"distance_m": float("nan")})["ok"]
        assert not hub.body.submit("frontflip", {})["ok"]
        assert len(sim_seen) == 1 or all(not ok for *_, ok in sim_seen[1:]), "a refused command reached the simulator"
        # STOP acts on both and latches the real dog
        r = client.post("/api/stop").json()
        assert r["real_state"] == "HALTED"
        n = len(sim_seen)
        assert not hub.body.submit("walk", {"distance_m": 0.1})["ok"] and len(sim_seen) == n
        r = client.post("/api/mode", json={"mode": "sim"}).json()
        assert r["ok"] and r["mode"] == "sim" and not r["armed"] and r["real_state"] == "DISARMED"
    finally:
        stop.set()


def test_both_mode_is_refused_without_the_real_switch():
    client, hub, _ = build(real_enabled=False)
    r = client.post("/api/mode", json={"mode": "both", "confirm": True}).json()
    assert not r["ok"] and "--real" in r["error"] and r["mode"] == "sim"


def test_commands_route_lists_the_go1_command_set():
    client, _, _ = build(real_enabled=False)
    r = client.get("/api/commands")
    assert r.status_code == 200
    assert set(r.json()) == {"walk", "turn", "stand", "stand_up", "lie_down", "recovery", "backflip", "jump_yaw",
                             "straight_hand", "dance", "damping"}


def test_heartbeat_comes_from_event_polls():
    client, hub, _ = build(real_enabled=True)
    client.post("/api/mode", json={"mode": "real", "confirm": True})
    before = hub.real._heartbeat
    time.sleep(0.05)
    client.get("/api/events")
    assert hub.real._heartbeat > before


def test_reset_demo_in_real_mode_does_not_move_or_halt_the_dog():
    client, hub, _ = build(real_enabled=True)
    client.post("/api/mode", json={"mode": "real", "confirm": True})
    hub.real.x = 1.0
    r = client.post("/api/reset-demo").json()
    assert r["ok"] and hub.real.x == 0.0 and hub.real.state == "IDLE"


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
    print(f"\n{len(tests) - failed}/{len(tests)} passed" if not failed else f"\n{failed} FAILED")
    sys.exit(1 if failed else 0)
