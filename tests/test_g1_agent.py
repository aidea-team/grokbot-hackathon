"""The G1 chat agent's bounded `move` tool: validation, closed loop on the simulator, timed open loop on the (fake) real robot.

    python tests/test_g1_agent.py
No robot, no network, no LLM call.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "g1"))

import g1_real  # noqa: E402
from g1_agent import AMOUNT, CRUISE, G1Agent  # noqa: E402
from g1_real import ARMED, RealG1  # noqa: E402
from g1_world import G1World  # noqa: E402


class Hub:
    def __init__(self, body):
        self.body, self.mode, self.restricted = body, "sim", False


class FakeLoco:
    def __init__(self):
        self.calls: list[tuple] = []

    def __getattr__(self, name):
        def call(*a, **k):
            self.calls.append((name, a))
            return (0, 500) if name == "GetFsmId" else 0
        return call


def test_validation() -> None:
    ag = G1Agent(Hub(None))
    bad = ({"steps": []}, {"steps": "x"}, {"steps": [{"action": "fly", "amount": 1}]},
           {"steps": [{"action": "walk_forward", "amount": 0.01}]}, {"steps": [{"action": "walk_forward", "amount": 50}]},
           {"steps": [{"action": "turn_left", "amount": 720}]}, {"steps": [{"action": "walk_forward", "amount": "a"}]},
           {"steps": [{"action": "walk_forward", "amount": 1}] * 5}, {})
    for a in bad:
        steps, err = ag._validate_steps(a)
        assert steps is None and err, a
    steps, err = ag._validate_steps({"steps": [{"action": "turn_left", "amount": 90}, {"action": "walk_forward", "amount": 1}]})
    assert steps == [("turn_left", 90.0), ("walk_forward", 1.0)], (steps, err)
    # the model never picks a speed, and every cruise speed is above the ~0.2 m/s floor where the real robot stops stepping
    assert all(max(abs(c) for c in v) >= 0.25 for v in CRUISE.values())
    assert set(AMOUNT) == set(CRUISE)


def test_sim_closed_loop_distance_and_angle() -> None:
    w = G1World(width=160, height=90)
    w.start()
    try:
        time.sleep(2)
        ag = G1Agent(Hub(w))
        ok, msg = ag._execute("move", {"steps": [{"action": "walk_forward", "amount": 0.8}]}, ag._epoch)
        assert ok, msg
        s1 = w.snapshot()
        assert 0.65 <= s1["x"] <= 1.2, (s1["x"], msg)  # stops near the asked distance (gait overshoot allowed)
        y0 = s1["yaw_deg"]
        ok, msg = ag._execute("move", {"steps": [{"action": "turn_left", "amount": 90}]}, ag._epoch)
        assert ok, msg
        dyaw = (w.snapshot()["yaw_deg"] - y0 + 180) % 360 - 180
        assert 70 <= dyaw <= 120, (dyaw, msg)
        assert not w.snapshot()["fallen"]
    finally:
        w.shutdown()


def test_real_open_loop_is_continuous_and_fast_enough() -> None:
    r, f = RealG1(), FakeLoco()
    r._loco, r.state = f, ARMED
    ag = G1Agent(Hub(r))
    ag.hub.mode = "real"
    t = time.monotonic()
    ok, msg = ag._execute("move", {"steps": [{"action": "walk_forward", "amount": 0.4}, {"action": "turn_left", "amount": 30}]}, ag._epoch)
    dt = time.monotonic() - t
    assert ok, msg
    moves = [c for c in f.calls if c[0] == "Move"]
    assert len(moves) >= 15, len(moves)  # ~1.8 s of commands at 10 Hz, not a 0.3 s burst
    assert all(abs(c[1][0]) >= 0.25 or abs(c[1][2]) >= 0.25 for c in moves), "a command below the stepping floor was sent"
    names = [c[0] for c in f.calls]
    first_stop = names.index("StopMove")
    assert all(n == "Move" for n in names[:first_stop]) and names[first_stop:].count("Move") == 0, "stopped between steps or kept moving"
    assert max(abs(c[1][0]) for c in moves) <= g1_real.REAL_MAX_VX
    assert 1.5 <= dt <= 6, dt


def test_interrupt_stops_the_robot() -> None:
    r, f = RealG1(), FakeLoco()
    r._loco, r.state = f, ARMED
    ag = G1Agent(Hub(r))
    ag.hub.mode = "real"
    import threading
    epoch = ag._epoch
    threading.Timer(0.5, lambda: setattr(ag, "_epoch", ag._epoch + 1)).start()
    ok, msg = ag._execute("move", {"steps": [{"action": "walk_forward", "amount": 3.0}]}, epoch)
    assert ok is False and "interrotto" in msg and any(c[0] == "StopMove" for c in f.calls)


def test_event_ids_never_restart_and_session_is_exposed() -> None:
    from fastapi.testclient import TestClient
    from g1_app import create_app
    w = G1World(width=160, height=90)
    w.start()
    try:
        c = TestClient(create_app(w))
        ag = c.app.state.agent
        ag._emit("user", text="uno")
        ag._emit("user", text="due")
        last = ag.events(0)[-1]["id"]
        ag.reset()  # what a mode switch / re-arm does
        ag._emit("user", text="tre")
        assert ag.events(0)[0]["id"] > last, "ids restarted after reset: the page would hide new messages"
        f1 = ag._store(b"x")
        ag.reset()
        assert ag._store(b"y") > f1, "frame ids restarted"
        ag._emit("user", text="quattro")
        r = c.get("/api/events?after=0").json()
        assert r["session"] == ag.session and [e["text"] for e in r["events"]] == ["quattro"]
    finally:
        w.shutdown()


def test_prompt_and_guard_against_micro_movement_loops() -> None:
    from g1_agent import MAX_CONSECUTIVE_MOVES, system_prompt
    from g1_agent import CRUISE, describe_call
    for real in (True, False):
        p = system_prompt(real)
        assert "UNA sola chiamata move" in p and "piccoli passi" not in p and "sii prudente" not in p
        for action in CRUISE:  # every locomotion primitive is explained in the prompt
            assert action in p, action
        assert "METRI" in p and "GRADI" in p and "CENTRO" in p and "mezzo metro" in p and "destra" in p
    assert describe_call("move", {"steps": [{"action": "walk_forward", "amount": 1}, {"action": "turn_left", "amount": 30}], "thought": "x"}) == \
        "move(walk forward 1 m -> turn left 30°)"
    assert "object" not in describe_call("move", {"steps": [{"action": "walk_forward", "amount": 1}]}).lower()
    assert MAX_CONSECUTIVE_MOVES <= 3


def test_mission_stops_a_model_that_keeps_nudging() -> None:
    """A scripted 'LLM' that asks for 5 small moves in a row: the 4th is refused, the prompts carry the cumulative displacement."""
    import json
    import os
    import types
    import openai
    from g1_agent import MAX_CONSECUTIVE_MOVES

    seen: list[str] = []
    script = [("move", {"steps": [{"action": "walk_forward", "amount": 0.2}], "thought": "t"})] * 5 + [("finish", {"message": "ok"})]

    class Resp:
        def __init__(self, name, args):
            self.output = [types.SimpleNamespace(type="function_call", name=name, arguments=json.dumps(args))]
            self.output_text = ""

    class FakeOpenAI:
        def __init__(self, **kw):
            self.responses = self
            self.i = 0

        def create(self, **kw):
            seen.append(kw["input"][0]["content"][0]["text"])
            name, args = script[min(self.i, len(script) - 1)]
            self.i += 1
            return Resp(name, args)

    r, f = RealG1(), FakeLoco()
    r._loco, r.state = f, ARMED
    r.head_jpeg = lambda timeout=3.0: b"jpeg"
    ag = G1Agent(Hub(r))
    ag.hub.mode = "real"
    real_openai, openai.OpenAI = openai.OpenAI, FakeOpenAI
    os.environ["OPENAI_API_KEY"] = "sk-test"
    try:
        ag._mission("vai avanti di un metro", ag._epoch, "real")
    finally:
        openai.OpenAI = real_openai
    steps = [e for e in ag.events(0) if e["kind"] == "step"]
    results = [(e["ok"], e["result"]) for e in steps]
    assert [ok for ok, _ in results[:MAX_CONSECUTIVE_MOVES]] == [True] * MAX_CONSECUTIVE_MOVES, results
    assert results[MAX_CONSECUTIVE_MOVES][0] is False and "movimenti di fila" in results[MAX_CONSECUTIVE_MOVES][1], results
    assert sum(1 for c in f.calls if c[0] == "StopMove") >= MAX_CONSECUTIVE_MOVES  # each executed move ended with a stop
    assert "avanti +0.60 m" in seen[MAX_CONSECUTIVE_MOVES], seen[MAX_CONSECUTIVE_MOVES]  # 3 x 0.2 m already commanded
    assert any(e["kind"] == "final" for e in ag.events(0))


def test_agent_gestures_follow_the_body_and_mock_flags_unsimulated() -> None:
    from fastapi.testclient import TestClient
    from g1_app import create_app
    r, f = RealG1(), FakeLoco()
    r._loco, r.state = f, ARMED
    r.actions = {"custom_dance": 101, "high_five": 18}
    ag = G1Agent(Hub(r))
    enum = [x for x in ag._tools() if x["name"] == "gesture"][0]["parameters"]["properties"]["name"]["enum"]
    assert "high_five" in enum and "clap" not in enum and "release_arm" not in enum
    assert "custom_dance" not in enum  # id 101 is not in Unitree's documented table: the chat does not get it by itself
    ok, msg = ag._execute("gesture", {"name": "clap"}, ag._epoch)
    assert ok is False  # not in this robot's list
    w = G1World(width=160, height=90)
    w.start()
    try:
        c = TestClient(create_app(w))
        ps = c.get("/api/presets").json()["presets"]
        assert any(p["name"] == "high_five" and p["simulated"] for p in ps)
        res = c.post("/api/preset", json={"name": "custom_dance"}).json()
        assert res["ok"] is False and "non è simulato" in res["error"]
    finally:
        w.shutdown()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
