"""Headless smoke test: load each model and step the physics for 1 s of simulated time."""
import mujoco

from models import MODELS, model_path

for name in MODELS:
    m = mujoco.MjModel.from_xml_path(str(model_path(name)))
    d = mujoco.MjData(m)
    while d.time < 1.0:
        mujoco.mj_step(m, d)
    print(f"{name}: nq={m.nq} nu={m.nu} stepped to t={d.time:.2f}s")
