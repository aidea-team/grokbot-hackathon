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
        assert c.post("/api/stop").json()["ok"] and c.post("/api/reset").json()["ok"]
        assert c.get("/api/state").json()["robot"] == "g1"
    finally:
        w.shutdown()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
