"""The simulator receives exactly the commands the real dog receives, and the world is the one we designed.

    python tests/test_sim.py        # plain runner
    python -m pytest tests

MuJoCo only, no hardware, no network. The physics is stepped by a helper thread (the app does it in the main thread).
"""
from __future__ import annotations

import math
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("chat", "dog", "sim"):
    sys.path.insert(0, str(ROOT / "src" / sub))

import commands  # noqa: E402
import mujoco  # noqa: E402
import scene  # noqa: E402
from dog_world import DogSim  # noqa: E402
from driver import PRIMITIVES  # noqa: E402
from real_body import RealBody  # noqa: E402
from sim_body import SimBody  # noqa: E402


class Running:
    """A SimBody whose world is stepped (faster than real time) by a helper thread."""

    def __init__(self):
        self.world = DogSim(headless=True)
        self.wire = []  # every (vx, vyaw, mode) that reaches the simulated UDP link
        orig = self.world.set_command
        self.world.set_command = lambda **kw: (self.wire.append((kw.get("vx"), kw.get("vyaw"), kw.get("mode"))), orig(**kw))[1]
        self.body = SimBody(self.world)
        self._stop = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()
        time.sleep(1.0)

    def _loop(self):
        while not self._stop.is_set():
            self.world.step(1 / 60)
            time.sleep(0.0005)

    def run(self, name, args=None, limit=90.0):
        r = self.body.submit(name, args or {})
        assert r["ok"], r
        t0 = time.monotonic()
        while not self.body.is_idle() and time.monotonic() - t0 < limit:
            time.sleep(0.02)
        assert self.body.is_idle(), f"{name} did not finish"
        return self.body.snapshot()

    def close(self):
        self._stop.set()
        self.body.shutdown()
        self.world.shutdown()


def test_simulator_and_real_dog_share_the_command_definition():
    from dog_agent import build_tools
    assert [t["name"] for t in build_tools("sim")] == [t["name"] for t in build_tools("real")]
    assert RealBody.tool_specs() == commands.tool_specs()
    assert set(commands.TOOLS) == {"walk", "turn", "stand", "stand_up", "lie_down", "recovery", "backflip", "jump_yaw",
                                   "straight_hand", "dance", "damping"}


def test_sim_and_real_refuse_the_same_malformed_commands():
    sim = Running()
    try:
        for name, args in (("frontflip", {}), ("sit", {}), ("walk", {}), ("walk", {"distance_m": float("nan")}),
                           ("turn", {"degrees": "90"}), ("dance", {"style": 3}), ("backflip", {"nope": 1})):
            assert not sim.body.submit(name, args)["ok"], (name, args)
            assert not commands.validate_args(name, args)[0]
    finally:
        sim.close()


def test_the_simulator_receives_what_the_dog_would_receive():
    sim = Running()
    try:
        sim.run("walk", {"distance_m": 0.4, "speed_mps": 0.4})
        walk_wire = [w for w in sim.wire if w[2] == "VEL_WALK"]
        assert walk_wire and all(abs(w[0] - 0.4) < 1e-9 and w[1] == 0.0 for w in walk_wire), "walk = a constant vx"
        sim.wire.clear()
        sim.run("turn", {"degrees": 20, "rate_dps": 40})
        turn_wire = [w for w in sim.wire if w[2] == "VEL_WALK"]
        assert turn_wire and all(w[0] == 0.0 and abs(w[1] - math.radians(40)) < 1e-9 for w in turn_wire)
        assert sim.wire[-1] == (0.0, 0.0, "IDLE"), "every command ends with IDLE, like the real driver"
        sim.wire.clear()
        for tool in ("stand_up", "lie_down", "stand_up", "recovery", "jump_yaw", "backflip", "straight_hand", "damping"):
            sim.run(tool, {"seconds": 1.0} if tool in ("straight_hand", "damping") else {})
        sim.run("dance", {"style": 2, "seconds": 2.0})
        sim.run("dance", {"style": 1, "seconds": 2.0})
        modes = {w[2] for w in sim.wire} - {"IDLE", "VEL_WALK"}
        assert modes == {m for m, _ in PRIMITIVES.values()}, f"modes on the wire: {modes}"
    finally:
        sim.close()


def test_every_primitive_does_what_its_mode_says():
    sim = Running()
    try:
        assert sim.run("lie_down")["z"] < 0.15
        before = sim.body.snapshot()
        after = sim.run("walk", {"distance_m": 1.0})
        assert abs(after["x"] - before["x"]) < 0.05, "a velocity from lying does nothing (assumption, see dog_world)"
        assert sim.run("stand_up")["z"] > 0.2
        yaw0 = sim.body.snapshot()["yaw_deg"]
        s = sim.run("jump_yaw")
        assert abs(((s["yaw_deg"] - yaw0 + 180) % 360) - 180) > 45, "JUMPYAW must turn the dog in the air"
        assert not sim.body.last_fell
        s = sim.run("backflip")
        assert s["z"] > 0.2 and s["posture"] != "caduto", "the backflip lands on its feet"
        assert sim.run("damping", {"seconds": 1.5})["z"] < 0.12, "DAMPING: legs go slack, the body drops"
        assert sim.run("recovery")["z"] > 0.2
        d = sim.run("dance", {"style": 1, "seconds": 3.0})
        assert d["z"] > 0.2
    finally:
        sim.close()


def test_stop_aborts_the_running_command_and_the_next_one_still_works():
    sim = Running()
    try:
        sim.body.submit("walk", {"distance_m": 5.0, "speed_mps": 0.5})
        time.sleep(1.5)
        t0 = time.monotonic()
        sim.body.clear()
        while not sim.body.is_idle() and time.monotonic() - t0 < 5:
            time.sleep(0.02)
        assert sim.body.is_idle() and time.monotonic() - t0 < 2.0
        s = sim.body.snapshot()
        assert s["x"] < 4.5
        assert sim.run("stand")["z"] > 0.2, "a STOP must not leave a latched halt in the simulator"
        sim.body.clear()  # STOP while idle must not poison the next command either
        assert sim.run("stand")["z"] > 0.2
    finally:
        sim.close()


# ----------------------------------------------------------------------------- the world
def _geoms(model):
    out = []
    for g in range(model.ngeom):
        name = model.geom(g).name
        if name:
            out.append((name.rsplit("_", 1)[0], model.geom_pos[g].copy(), model.geom_size[g].copy(),
                        int(model.geom_type[g]), int(model.geom_bodyid[g])))
    return out


def test_two_empty_metres_ahead_then_stairs():
    m = scene.build_model()
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    xs = [float(d.geom_xpos[g][0] - m.geom_size[g][0]) for g in range(m.ngeom)
          if m.geom(g).name.rsplit("_", 1)[0] in ("stairs", "platform", "scaffold")]
    assert min(xs) >= 2.0 - 1e-6, f"something starts at x={min(xs):.2f}, inside the 2 m empty zone"
    stairs = [float(d.geom_xpos[g][0] - m.geom_size[g][0]) for g in range(m.ngeom) if m.geom(g).name.startswith("stairs")]
    assert abs(min(stairs) - 2.0) < 1e-6, f"stairs must start at x=2.0, got {min(stairs)}"


def test_platforms_only_at_the_sides_of_the_stair_line():
    m = scene.build_model()
    plats = [(p, s) for label, p, s, *_ in _geoms(m) if label == "platform"]
    assert len(plats) == 6
    assert all(abs(p[1]) - s[1] > 1.5 for p, s in plats), "a platform on the stair line"
    assert sum(p[1] > 0 for p, _ in plats) == 3 and sum(p[1] < 0 for p, _ in plats) == 3


def test_five_barriers_of_growing_height_behind_the_dog():
    m = scene.build_model()
    bars = sorted(((p[0], 2 * s[2]) for label, p, s, *_ in _geoms(m) if label == "barrier"), reverse=True)
    assert len(bars) == 5 and all(x < 0 for x, _ in bars)
    heights = [h for _, h in bars]
    assert heights == sorted(heights) and len(set(heights)) == 5, f"heights not strictly growing: {heights}"
    assert abs(heights[0] - 0.10) < 1e-6 and abs(heights[-1] - 0.60) < 1e-6


def test_a_life_size_person_stands_behind_the_barriers():
    m = scene.build_model()
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    top, xs = 0.0, []
    for g in range(m.ngeom):
        if m.geom(g).name.startswith("person"):
            z, r = d.geom_xpos[g][2], m.geom_size[g]
            half = r[0] if m.geom_type[g] == int(mujoco.mjtGeom.mjGEOM_SPHERE) else (
                r[1] + r[0] if m.geom_type[g] == int(mujoco.mjtGeom.mjGEOM_CAPSULE) else r[2])
            top = max(top, z + half)
            xs.append(d.geom_xpos[g][0])
    assert 1.65 <= top <= 1.85, f"person is {top:.2f} m tall"
    assert max(xs) < min(-5.5, -5.5 - 0.1), "the person must be past the last barrier"


def test_the_dog_climbs_the_stairs_onto_the_scaffold_and_cannot_get_up_from_the_side():
    sim = Running()
    try:
        s = sim.run("walk", {"distance_m": 1.3, "speed_mps": 0.6})
        assert s["x"] < 2.0 and s["z"] < 0.3, "still on the empty floor"
        for _ in range(8):  # open loop: it covers less than commanded, so (like the agent) walk, look, walk again
            s = sim.run("walk", {"distance_m": 1.0, "speed_mps": 0.6})
            if s["z"] > 0.6:
                break
        assert s["z"] > 0.6 and s["x"] > 3.6, f"did not reach the scaffold: {s}"
    finally:
        sim.close()
    sim = Running()
    try:  # from the side: the rails block (turn left, go to y=1.6, turn right, walk at the scaffold from the side)
        sim.run("turn", {"degrees": 90, "rate_dps": 60})
        sim.run("walk", {"distance_m": 1.5, "speed_mps": 0.6})
        sim.run("turn", {"degrees": -90, "rate_dps": 60})
        s = sim.run("walk", {"distance_m": 5.0, "speed_mps": 0.6})
        assert s["z"] < 0.3, "the dog got onto the scaffold without the stairs"
    finally:
        sim.close()


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
