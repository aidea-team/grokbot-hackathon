"""Open the interactive MuJoCo viewer on a model.

macOS: run with `mjpython src/sim/view.py go1` (plain `python` fails for the viewer).
Linux/Windows: plain `python` works.
"""
import argparse

import mujoco
import mujoco.viewer

from models import MODELS, model_path

ap = argparse.ArgumentParser()
ap.add_argument("model", nargs="?", default="go1", choices=sorted(MODELS))
args = ap.parse_args()

m = mujoco.MjModel.from_xml_path(str(model_path(args.model)))
d = mujoco.MjData(m)
mujoco.viewer.launch(m, d)
