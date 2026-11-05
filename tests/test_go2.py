"""The Go2 backend: commands, drivers (mock + real driver over a fake WebRTC link), hub robot switch, HTTP API.
No hardware, no network, no `unitree_webrtc_connect` needed.

    python tests/test_go2.py
"""
from __future__ import annotations

import math
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("chat", "dog", "sim"):
    sys.path.insert(0, str(ROOT / "src" / sub))

from fastapi.testclient import TestClient  # noqa: E402

import go2_commands as g2  # noqa: E402
import go2_bodies  # noqa: E402
from app import create_app  # noqa: E402
from dog_agent import DogAgent, build_tools, system_prompt  # noqa: E402
from dog_world import DogSim  # noqa: E402
from driver import JsonlLog  # noqa: E402
from go2_driver import Go2Driver, Go2Link, Go2MockDriver  # noqa: E402
from hub import RobotHub  # noqa: E402
from real_body import RealBody  # noqa: E402
from sim_body import SimBody  # noqa: E402


class ListLog:
    def __init__(self):
        self.events = []
        self.path = Path(tempfile.mkdtemp()) / "log.jsonl"

    def event(self, kind, **f): self.events.append({"event": kind, **f})


class FakeLink:
    """Stands in for Go2Link: records every sport command."""

    def __init__(self):
        self.calls, self.connected = [], False
        self.addr = None
        self.camera = type("Cam", (), {"frame": b"\xff\xd8x\xff\xd9", "error": None,
                                       "acquire": lambda s: None, "release": lambda s: None})()

    def connect(self): self.connected = True; return {"addr": "fake", "soc": 77, "model": "Go2"}
    def disconnect(self): self.connected = False
    def sport(self, name, parameter=None, timeout=5.0): self.calls.append((name, parameter)); return 0
    def move(self, vx, vy, vyaw): self.calls.append(("Move", {"x": vx, "y": vy, "z": vyaw}))
    def stop_move(self): self.calls.append(("StopMove", None))


def names(link): return [c[0] for c in link.calls]


# ---------------------------------------------------------------------------------------------- commands
def test_commands_have_no_damp_no_flips_and_a_matching_spec_per_tool():
    assert set(g2.tool_specs()) == set(g2.TOOLS)
    for banned in ("damping", "backflip", "frontflip", "jump_yaw"):
        assert banned not in g2.TOOLS
    assert "strafe" in g2.TOOLS


def test_validation_is_type_only_and_refuses_garbage():
    assert g2.validate_args("walk", {"distance_m": 100, "speed_mps": 5})[0], "no numeric limits"
    assert g2.validate_args("strafe", {"distance_m": -0.5})[2] == {"distance_m": -0.5, "speed_mps": g2.DEFAULT_WALK_SPEED}
    for name, args in (("walk", {}), ("walk", {"distance_m": float("nan")}), ("walk", {"distance_m": True}),
                       ("walk", {"distance_m": 1, "bogus": 2}), ("turn", {"degrees": 0}), ("dance", {"style": 3}),
                       ("sit", {"seconds": 0}), ("damping", {}), ("backflip", {}), ("strafe", {"distance_m": "1"})):
        assert not g2.validate_args(name, args)[0], (name, args)


# ---------------------------------------------------------------------------------------------- mock driver
def test_mock_driver_walk_strafe_turn_integrate_the_pose():
    d = Go2MockDriver(ListLog())
    d.connect()
    g2.execute(d, "walk", {"distance_m": 0.2, "speed_mps": 0.5})
    assert abs(d.x - 0.2) < 0.05 and abs(d.y) < 0.01
    g2.execute(d, "strafe", {"distance_m": 0.2, "speed_mps": 0.5})
    assert abs(d.y - 0.2) < 0.05, "positive strafe = left (+y)"
    g2.execute(d, "turn", {"degrees": 20, "rate_dps": 100})
    assert abs(math.degrees(d.yaw) - 20) < 6
    assert g2.execute(d, "hello", {"seconds": 0.2}).ok


# ---------------------------------------------------------------------------------------------- real driver
def test_go2_driver_sends_sport_commands_once_for_tricks_and_streams_move():
    link = FakeLink()
    d = Go2Driver(ListLog(), link)
    assert d.connect()["soc"] == 77
    g2.execute(d, "hello", {"seconds": 0.2})
    assert names(link).count("Hello") == 1, "tricks are one-shot, not repeated"
    link.calls.clear()
    g2.execute(d, "walk", {"distance_m": 0.1, "speed_mps": 0.5})
    assert names(link)[0] == "BalanceStand", "Move is preceded by BalanceStand after a posture command"
    moves = [c[1] for c in link.calls if c[0] == "Move"]
    assert len(moves) >= 3 and all(m["x"] == 0.5 and m["y"] == 0 and m["z"] == 0 for m in moves)
    assert names(link)[-1] == "StopMove", "every movement ends with StopMove"
    link.calls.clear()
    g2.execute(d, "strafe", {"distance_m": -0.1, "speed_mps": 0.5})
    assert all(m[1]["y"] == -0.5 and m[1]["x"] == 0 for m in link.calls if m[0] == "Move") and "Move" in names(link)
    link.calls.clear()
    g2.execute(d, "turn", {"degrees": 10, "rate_dps": 60})
    assert all(m[1]["z"] > 0 for m in link.calls if m[0] == "Move"), "positive degrees = positive yaw (left)"
    assert "Damp" not in [c[0] for c in link.calls]
    d.close()
    assert not link.connected


def test_halt_sends_stopmove_immediately_and_interrupts():
    import threading
    link = FakeLink()
    d = Go2Driver(ListLog(), link)
    d.connect()
    res = {}
    t = threading.Thread(target=lambda: res.update(r=g2.execute(d, "walk", {"distance_m": 5, "speed_mps": 0.1})))
    t.start()
    time.sleep(0.4)
    link.calls.clear()
    d.halt()
    assert link.calls and link.calls[0][0] == "StopMove", "halt() acts at once, from the calling thread"
    t.join(5)
    assert not t.is_alive() and res["r"].interrupted
    assert not d.primitive("hello").ok, "a halted driver refuses new commands"


def test_connect_failure_is_a_connection_error():
    class Bad(FakeLink):
        def connect(self): raise ConnectionError("RobotBusyError: chiudi l'app")
    try:
        Go2Driver(ListLog(), Bad()).connect()
    except ConnectionError as e:
        assert "chiudi" in str(e)
    else:
        raise AssertionError("expected ConnectionError")


def test_real_link_without_the_library_explains_what_to_install():
    saved = {k: v for k, v in sys.modules.items() if k.startswith("unitree_webrtc_connect")}
    for k in saved:
        del sys.modules[k]
    sys.modules["unitree_webrtc_connect"] = None  # makes `import unitree_webrtc_connect...` raise ImportError
    try:
        Go2Link().connect(timeout=5)
    except ConnectionError as e:
        assert "unitree_webrtc_connect" in str(e)
    else:
        raise AssertionError("expected ConnectionError")
    finally:
        del sys.modules["unitree_webrtc_connect"]
        sys.modules.update(saved)


# ---------------------------------------------------------------------------------------------- body + hub + API
def build(go2_real: bool):
    log = ListLog()
    sim = SimBody(DogSim(headless=True, log=log), log)
    link = FakeLink()
    g_real = RealBody(lambda lg: Go2Driver(lg, link), log, camera=link.camera, cmds=g2, robot="go2") if go2_real else None
    hub = RobotHub(sim, None, log, go2_sim=go2_bodies.make_go2_mock(log), go2_real=g_real)
    return TestClient(create_app(hub, sim, DogAgent(hub, log))), hub, link


def wait_idle(hub, t=30):
    t0 = time.monotonic()
    while not hub.body.is_idle() and time.monotonic() - t0 < t:
        time.sleep(0.02)
    assert hub.body.is_idle()


def test_robot_switch_lands_on_the_go2_mock_and_back():
    client, hub, _ = build(go2_real=False)
    s = client.get("/api/state").json()
    assert s["robot"] == "go1" and s["robots"] == ["go1", "go2"]
    r = client.post("/api/robot", json={"robot": "go2"}).json()
    assert r["ok"] and r["robot"] == "go2" and r["mode"] == "sim"
    assert client.get("/api/state").json()["robot"] == "go2"
    assert set(client.get("/api/commands").json()) == set(g2.TOOLS)
    assert [c["name"] for c in client.get("/api/cameras").json()["cameras"]] == ["front"]
    jpeg = client.get("/api/camera.jpg?cam=front")
    assert jpeg.status_code == 200 and jpeg.content[:2] == b"\xff\xd8", "the mock Go2 has a synthetic camera"
    assert client.get("/api/camera.jpg?cam=side").status_code == 404
    r = client.post("/api/robot", json={"robot": "go1"}).json()
    assert r["ok"] and r["robot"] == "go1"
    assert not client.post("/api/robot", json={"robot": "go3"}).json()["ok"]


def test_go2_mock_runs_manual_commands_wasd_and_stop_does_not_latch():
    client, hub, _ = build(go2_real=False)
    client.post("/api/robot", json={"robot": "go2"})
    assert client.post("/api/manual", json={"command": "strafe", "args": {"distance_m": 0.1, "speed_mps": 0.5}}).json()["ok"]
    wait_idle(hub)
    assert hub.body.snapshot()["y"] > 0.05 and hub.body.snapshot()["robot"] == "go2"
    for bad in ("damping", "backflip", "jump_yaw"):
        assert not client.post("/api/manual", json={"command": bad, "args": {}}).json()["ok"], bad
    for _ in range(8):
        client.post("/api/teleop", json={"fwd": 1, "turn": 0, "speed": 0.3, "rate": 30})
        time.sleep(0.1)
    assert hub.body.snapshot()["x"] > 0.03
    client.post("/api/teleop", json={"fwd": 0, "turn": 0})
    time.sleep(0.4)
    client.post("/api/manual", json={"command": "dance", "args": {"style": 1, "seconds": 5}})
    time.sleep(0.2)
    assert client.post("/api/stop").json()["ok"]
    time.sleep(0.5)
    assert hub.go2_sim.state == "IDLE", "the mock must stay usable after Stop"
    assert client.post("/api/manual", json={"command": "stand", "args": {}}).json()["ok"]


def test_go2_both_mode_and_real_without_the_switch_are_refused():
    client, hub, _ = build(go2_real=False)
    client.post("/api/robot", json={"robot": "go2"})
    r = client.post("/api/mode", json={"mode": "real", "confirm": True}).json()
    assert not r["ok"] and "--real" in r["error"] and r["mode"] == "sim"
    assert client.get("/cam/1.mjpg").status_code == 404
    client2, hub2, _ = build(go2_real=True)
    client2.post("/api/robot", json={"robot": "go2"})
    r = client2.post("/api/mode", json={"mode": "both", "confirm": True}).json()
    assert not r["ok"] and "Go1" in r["error"]


def test_go2_real_needs_confirm_arms_connects_and_stop_latches():
    client, hub, link = build(go2_real=True)
    client.post("/api/robot", json={"robot": "go2"})
    assert not client.post("/api/mode", json={"mode": "real"}).json()["ok"] and not link.connected
    r = client.post("/api/mode", json={"mode": "real", "confirm": True}).json()
    assert r["ok"] and r["mode"] == "real" and r["real_state"] == "IDLE" and r["armed"] and r["battery"] == 77
    assert link.connected and hub.body is hub.go2_real
    assert client.post("/api/manual", json={"command": "hello", "args": {"seconds": 0.2}}).json()["ok"]
    wait_idle(hub)
    assert "Hello" in names(link)
    assert client.post("/api/manual", json={"command": "walk", "args": {"distance_m": 5, "speed_mps": 0.1}}).json()["ok"]
    time.sleep(0.4)
    link.calls.clear()
    r = client.post("/api/stop").json()
    assert r["real_state"] == "HALTED" and "StopMove" in names(link)
    time.sleep(0.5)
    assert not client.post("/api/manual", json={"command": "stand", "args": {}}).json()["ok"]
    assert client.post("/api/mode", json={"mode": "real", "confirm": True}).json()["real_state"] == "IDLE", "explicit re-arm"
    # switching robot disarms the real Go2 and lands on the Go1 simulator
    r = client.post("/api/robot", json={"robot": "go1"}).json()
    time.sleep(0.8)  # the driver is closed on a background thread
    assert r["robot"] == "go1" and r["mode"] == "sim" and hub.go2_real.state == "DISARMED" and not link.connected


def test_failed_go2_connection_stays_on_the_mock():
    class Bad(FakeLink):
        def connect(self): raise ConnectionError("no route")
    log = ListLog()
    link = Bad()
    sim = SimBody(DogSim(headless=True, log=log), log)
    hub = RobotHub(sim, None, log, go2_sim=go2_bodies.make_go2_mock(log),
                   go2_real=RealBody(lambda lg: Go2Driver(lg, link), log, camera=link.camera, cmds=g2, robot="go2"))
    client = TestClient(create_app(hub, sim, DogAgent(hub, log)))
    client.post("/api/robot", json={"robot": "go2"})
    r = client.post("/api/mode", json={"mode": "real", "confirm": True}).json()
    assert not r["ok"] and "no route" in r["error"] and r["mode"] == "sim" and not r["armed"]


# ---------------------------------------------------------------------------------------------- agent
def test_agent_tools_and_prompts_follow_the_robot():
    t2 = [t["name"] for t in build_tools("sim", True, "go2")]
    assert t2[-1] == "finish" and set(t2[:-1]) == set(g2.TOOLS) and "damping" not in t2
    t1 = [t["name"] for t in build_tools("sim", True, "go1")]
    assert "damping" in t1 and "strafe" not in t1
    for mode in ("sim", "real"):
        p = system_prompt(mode, None, "go2")
        assert "Go2" in p and "Go1" not in p and "cam1" in p and "cam2" not in p
    assert "REALE" in system_prompt("real", None, "go2") and "SINTETICA" in system_prompt("sim", None, "go2")
