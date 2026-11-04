"""RealG1 may send only the high-level calls we allow: walking, a whitelist of FSM modes, stand height, balance mode, gestures.
Never developer mode, never low level, never zero torque.

    python tests/test_g1_real_safety.py
No robot, no network: fake LocoClient / arm-action client record every call.
"""
from __future__ import annotations

import ast
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "g1"))

import g1_real  # noqa: E402
from g1_real import ARMED, RealError, RealG1  # noqa: E402

LOCO_ALLOWED = {"Move", "StopMove", "GetFsmId", "SetFsmId", "HighStand", "LowStand", "SetBalanceMode", "WaveHand"}
ARM_ALLOWED = {"ExecuteAction", "GetActionList", "_Call", "_RegistApi"}  # GetActionList is a read; _Call carries the documented ids below
ARM_API_IDS = {7106, 7107, 7108, 7113}  # execute, list, execute-custom (by name), stop-custom: the robot's own arm service


class Fake:
    def __init__(self):
        self.calls: list[tuple] = []

    def __getattr__(self, name):
        def call(*a, **k):
            self.calls.append((name, a))
            if name == "GetFsmId":
                return 0, 500
            if name == "_Call":
                return 0, ""
            return 0
        return call


def armed() -> tuple[RealG1, Fake, Fake]:
    r, f, a = RealG1(), Fake(), Fake()
    r._loco, r._arm_client, r.state = f, a, ARMED
    r.FSM_WAIT_S = 0
    return r, f, a


def test_allowed_calls_only() -> None:
    r, f, a = armed()
    r.command(0.3, 0.0, 0.2)
    r.command(99, 99, 99)  # clipped to the real ceilings, still just Move
    last = r._cmd
    assert abs(last[0]) <= g1_real.REAL_MAX_VX and abs(last[1]) <= g1_real.REAL_MAX_VY and abs(last[2]) <= g1_real.REAL_MAX_VYAW, last
    r.stop()
    for fsm in (500, 501, 3, 706):
        r.set_fsm(fsm)
    r.reset()
    r.stand_height(True)
    r.stand_height(False)
    r.balance_mode(0)
    r.balance_mode(1)
    assert r.play("wave_hand") and r.play("wave_hand_turn") and r.play("clap") and r.play("shake_hand")
    assert r.play("not_a_gesture") is False
    r.kill("test")
    assert {c[0] for c in f.calls} <= LOCO_ALLOWED, {c[0] for c in f.calls}
    assert {c[0] for c in a.calls} <= ARM_ALLOWED
    assert ("ExecuteAction", (17,)) in a.calls and ("ExecuteAction", (27,)) in a.calls  # clap, shake_hand


def test_refusals() -> None:
    r, f, a = armed()
    for fn, args in ((r.jog, ({"left_shoulder_pitch": 1},)), (r.set_pose, ({},)), (r.set_fsm, (0,)), (r.set_fsm, (1,)), (r.set_fsm, (702,)), (r.damp, ()), (r.set_fsm, (802,)),
                     (r.set_fsm, (9999,)), (r.balance_mode, (5,))):
        try:
            fn(*args)
            raise AssertionError(f"{fn.__name__}{args} was not refused")
        except RealError:
            pass
    assert not [c for c in f.calls if c[0] in ("SetFsmId", "SetBalanceMode")], f.calls  # nothing refused reached the robot (no Damp, no 702)
    assert not a.calls


def test_no_low_level_or_developer_mode_in_the_source() -> None:
    tree = ast.parse(Path(g1_real.__file__).read_text())
    for node in ast.walk(tree):  # drop docstrings (they say what we do NOT do); comments are not in the AST
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(getattr(node.body[0], "value", None), ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
    code = ast.unparse(tree)
    for banned in ("ZeroTorque", "SwitchToUserCtrl", "SwitchToInternalCtrl", "SelectMode", "ReleaseMode", "MotionSwitcher", "LowCmd_",
                   "ChannelPublisher", "rt/lowcmd", "rt/arm_sdk", ".Damp(", "Lie2StandUp("):
        assert banned not in code.replace("REFUSAL", ""), f"{banned} found in g1_real.py"


def test_watchdog_stops_when_silent() -> None:
    r, f, a = armed()
    r._watchdog = None
    r.command(0.3, 0, 0)
    threading.Thread(target=r._watchdog_loop, daemon=True).start()
    time.sleep(0.9)
    r._stop = True
    assert any(c[0] == "StopMove" for c in f.calls)


def test_refuses_when_not_armed() -> None:
    r = RealG1()
    for fn, args in ((r.command, (0.3, 0, 0)), (r.set_fsm, (500,)), (r.play, ("wave_hand",)), (r.stand_height, (True,))):
        try:
            fn(*args)
            raise AssertionError(f"{fn.__name__} acted while disarmed")
        except RealError:
            pass


def test_parse_action_list_formats() -> None:
    from g1_real import parse_action_list
    assert parse_action_list([{"id": 101, "name": "Custom Dance"}, {"action_id": "18", "action_name": "high five"}]) == {"custom_dance": 101, "high_five": 18}
    assert parse_action_list({"data": [{"id": 1, "name": "Wave!"}]}) == {"wave": 1}
    assert parse_action_list({"clap": 17, "hug": 19}) == {"clap": 17, "hug": 19}
    assert parse_action_list({"11": "two-hand kiss"}) == {"two_hand_kiss": 11}
    assert parse_action_list('[{"id": 5, "name": "x ray"}]') == {"x_ray": 5}
    assert parse_action_list([{"id": 7, "name": "挥手"}]) == {"action_7": 7}  # a name with no latin letters still gets a usable id-based name
    for junk in (None, [], {}, "nope", [{"foo": 1}], 42):
        assert parse_action_list(junk) == {}, junk


def test_real_runs_only_what_the_robot_lists() -> None:
    r, f, a = armed()

    def get_list():
        a.calls.append(("GetActionList", ()))
        return 0, [{"id": 101, "name": "Custom Dance"}, {"id": 18, "name": "high five"}]
    a.GetActionList = get_list
    r._load_actions(cache=None)
    assert r.actions == {"custom_dance": 101, "high_five": 18} and r.actions_source == "robot"
    assert "custom_dance" in r.gesture_names() and "wave_hand" in r.gesture_names() and "clap" not in r.gesture_names()
    assert r.play("custom_dance") and ("ExecuteAction", (101,)) in a.calls
    assert r.play("clap") is False  # the SDK's example table has it, this robot does not list it: never sent
    assert not [c for c in a.calls if c[0] == "ExecuteAction" and c[1] == (17,)]
    # a robot whose list cannot be read keeps working with the SDK table
    r2, f2, a2 = armed()
    a2.GetActionList = lambda: (3102, None)
    r2._load_actions(cache=None)
    assert r2.actions_source != "robot" and "clap" in r2.gesture_names()


REAL_REPLY = [  # shape of the real GetActionList reply of this G1 (2026-11-04): built-in actions with id, then actions taught in the app
    [{"id": 99, "name": "release_arm"}, {"id": 1, "name": "turn_back_wave"}, {"id": 18, "name": "high_five"}, {"id": 36, "name": "forward_push"}],
    [{"name": "Abbraccio", "time": 6.2}, {"name": "Fumare\nFumare", "time": 7.1}],
]


def test_parse_the_real_two_group_reply() -> None:
    from g1_real import parse_action_groups
    builtin, custom = parse_action_groups(REAL_REPLY)
    assert builtin == {"release_arm": 99, "turn_back_wave": 1, "high_five": 18, "forward_push": 36}
    assert custom == [{"name": "Abbraccio", "time": 6.2}, {"name": "Fumare\nFumare", "time": 7.1}]
    assert parse_action_groups([]) == ({}, []) and parse_action_groups(None) == ({}, [])


def test_taught_actions_by_name_and_agent_gesture_limits() -> None:
    r, f, a = armed()
    a.GetActionList = lambda: (0, REAL_REPLY)
    r._load_actions(cache=None)
    assert [c["name"] for c in r.custom_actions] == ["Abbraccio", "Fumare\nFumare"]
    # taught moves run by their exact name through API 7108; unknown names are never sent
    assert r.play_custom("Abbraccio") is True
    assert ("_Call", (7108, '{"action_name": "Abbraccio"}')) in a.calls
    n = len(a.calls)
    assert r.play_custom("Inventata") is False and len(a.calls) == n
    # kill also asks the arm service to stop a taught move (7113)
    r.kill("test")
    assert ("_Call", (7113, "{}")) in a.calls
    assert {c[1][0] for c in a.calls if c[0] == "_Call"} <= ARM_API_IDS
    # the chat only gets the actions of Unitree's documented table: not the extras ('may cause the robot to fall'), not release, not taught
    ag = r.agent_gestures()
    assert "high_five" in ag and "forward_push" not in ag and "turn_back_wave" not in ag and "release_arm" not in ag
    assert "Abbraccio" not in ag and "wave_hand" in ag
    assert "forward_push" in r.gesture_names()  # a human can still trigger it from the page
    # a refusal from the robot is reported, not swallowed
    a._Call = lambda api, p: (3102, "")
    try:
        r.state = ARMED
        r.play_custom("Abbraccio")
        raise AssertionError("refusal swallowed")
    except RealError:
        pass


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
