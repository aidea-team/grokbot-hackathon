"""G1 humanoid in MuJoCo: the standard locomotion policy (numpy) keeps it up and follows high-level commands.

    python tests/test_g1.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "g1"))

import numpy as np  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from g1_app import create_app  # noqa: E402
from g1_policy import LstmPolicy  # noqa: E402
from g1_world import MAX_VX, G1World  # noqa: E402


def hold(w: G1World, cmd, secs: float) -> None:
    t = time.monotonic()
    while time.monotonic() - t < secs:
        w.command(*cmd)
        time.sleep(0.1)


def test_policy_shape_and_state() -> None:
    p = LstmPolicy()
    a = p(np.zeros(47, np.float32))
    assert a.shape == (12,) and np.isfinite(a).all()
    p.reset()
    assert np.allclose(p(np.zeros(47, np.float32)), a)  # reset clears the LSTM state


def test_walks_turns_stands_and_resets() -> None:
    w = G1World(width=160, height=90)
    w.start()
    try:
        time.sleep(1)
        x0 = w.snapshot()["x"]
        hold(w, (0.5, 0, 0), 4)
        s = w.snapshot()
        assert not s["fallen"] and s["x"] - x0 > 1.0, s  # ~0.45 m/s measured
        yaw0 = s["yaw_deg"]
        hold(w, (0, 0, 0.8), 3)
        assert abs(w.snapshot()["yaw_deg"] - yaw0) > 40
        hold(w, (99, 0, 0), 1)  # out of envelope: clipped, not a fall
        assert w.snapshot()["vx"] <= MAX_VX + 1e-6
        hold(w, (0, 0, 0), 2)
        assert not w.snapshot()["fallen"] and w.snapshot()["z"] > 0.7
        w.reset()
        time.sleep(1)
        s = w.snapshot()
        assert abs(s["x"]) < 0.2 and s["falls"] == 0
    finally:
        w.shutdown()


def test_http_api() -> None:
    w = G1World(width=160, height=90)
    w.start()
    try:
        c = TestClient(create_app(w))
        assert c.get("/").status_code == 200
        assert c.post("/api/move", json={"vx": 0.3}).json()["ok"]
        assert c.post("/api/stop").json()["ok"] and c.post("/api/start").json()["ok"]
        assert c.get("/api/state").json()["robot"] == "g1"
    finally:
        w.shutdown()


def test_like_the_real_one_default_and_toggle() -> None:
    w = G1World(width=160, height=90)
    w.start()
    try:
        c = TestClient(create_app(w))
        assert c.get("/api/state").json()["locomotion_only"] is True  # default: the mock accepts what the real robot accepts
        for route, body in (("/api/jog", {"rates": {"left_shoulder_pitch": 1}}), ("/api/pose", {"pose": {}})):
            assert c.post(route, json=body).json()["ok"] is False, route  # joint-level arm control = low level: not like the real one
        assert c.post("/api/move", json={"vx": 0.3}).json()["ok"]
        assert c.post("/api/preset", json={"name": "high_wave"}).json()["ok"]  # gestures exist on the real robot too
        assert c.post("/api/move", json={"vx": 0.3}).json()["ok"] is False  # walking does not answer while a gesture runs (as on the real robot)
        w.stop()
        assert c.post("/api/fsm", json={"id": 1}).json()["ok"] is False  # no Damp like the real robot
        assert c.post("/api/damp").json()["ok"] is False
        assert c.post("/api/fsm", json={"id": 706}).json()["ok"] is False  # not simulated
        assert c.post("/api/start").json()["ok"]
        assert c.post("/api/locomotion_only", json={"value": False}).json()["locomotion_only"] is False
        assert c.post("/api/jog", json={"rates": {"left_shoulder_pitch": 1}}).json()["ok"]
        assert c.post("/api/fsm", json={"id": 1}).json()["fsm"] == 1  # the mock can damp only with "come il reale" off
        assert c.post("/api/start").json()["ok"]
        assert c.post("/api/locomotion_only", json={"value": True}).json()["locomotion_only"] is True
    finally:
        w.shutdown()


def test_lab29_policy_observation_and_action_shapes() -> None:
    from g1_policy_lab import DEFAULT, JOINT_IDS_MAP, LabPolicy
    p = LabPolicy()
    q = np.zeros(29, np.float32)
    q[JOINT_IDS_MAP] = DEFAULT  # robot already in the default pose
    obs = p.observe(np.zeros(3), np.array([0, 0, -1.0]), np.zeros(3), q, np.zeros(29))
    assert obs.shape == (480,) and np.isfinite(obs).all()
    a = p.act(obs)
    assert a.shape == (29,) and np.isfinite(a).all()
    assert p.targets().shape == (29,)
    assert sorted(JOINT_IDS_MAP) == list(range(29))  # a permutation of the 29 motors


def test_lab29_walks_without_falling_and_app_switch() -> None:
    w = G1World(width=160, height=90, controller="lab29")
    w.start()
    try:
        time.sleep(2)
        x0 = w.snapshot()["x"]
        hold(w, (0.5, 0, 0), 4)
        s = w.snapshot()
        assert not s["fallen"] and s["x"] - x0 > 1.0, s
        assert s["controller"] == "lab29"
        c = TestClient(create_app(w))
        r = c.post("/api/locomotion_only", json={"value": False}).json()
        assert c.post("/api/jog", json={"rates": {"left_shoulder_pitch": 1}}).json()["ok"] is False  # the policy owns the arms
        assert c.post("/api/preset", json={"name": "clap"}).json()["ok"] is False
        assert c.post("/api/controller", json={"name": "gym12"}).json()["ok"]
        time.sleep(2)
        assert c.get("/api/state").json()["controller"] == "gym12" and not w.snapshot()["fallen"]
        assert c.post("/api/controller", json={"name": "nope"}).json()["ok"] is False
    finally:
        w.shutdown()


def test_two_cylinders_4m_ahead_red_right_blue_left() -> None:
    import io
    from PIL import Image
    w = G1World(width=320, height=180, head_size=(640, 360))
    w.start()
    try:
        g = {n: w.model.geom(n).pos.copy() for n in ("cyl_red", "cyl_blue")}
        assert abs(g["cyl_red"][0] - 4) < 0.1 and abs(g["cyl_blue"][0] - 4) < 0.1  # 4 m ahead of the start
        assert g["cyl_red"][1] < 0 < g["cyl_blue"][1]  # right = -y, left = +y
        assert abs(g["cyl_red"][1] + 1.2) < 0.05 and abs(g["cyl_blue"][1] - 1.2) < 0.05  # 2.4 m apart
        assert all(abs(w.model.geom(n).size[1] * 2 - 1.2) < 0.05 for n in g)  # 1.2 m tall
        time.sleep(1.5)
        w.reset()
        time.sleep(1.5)
        im = np.asarray(Image.open(io.BytesIO(w.head_jpeg())).convert("RGB")).astype(int)
        r, gg, b = im[..., 0], im[..., 1], im[..., 2]
        red, blue = (r > 150) & (gg < 70) & (b < 70), (b > 150) & (r < 70) & (gg < 120)
        assert red.sum() > 100 and blue.sum() > 100, (red.sum(), blue.sum())
        W = im.shape[1]
        assert np.nonzero(red)[1].mean() > W / 2 > np.nonzero(blue)[1].mean(), "red should be on the right of the head camera, blue on the left"
    finally:
        w.shutdown()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
