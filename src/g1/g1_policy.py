"""Unitree's standard G1 locomotion policy (unitree_rl_gym, deploy/pre_train/g1/motion.pt), in plain numpy.

The TorchScript file is an LSTM(47 -> 64) followed by an MLP 64 -> 32 -> 12 (ELU). We keep the weights in
motion_weights.npz (dumped once from motion.pt) so the runtime needs no torch.
Observation (47): ang_vel*0.25 (3), gravity in body frame (3), cmd*[2,2,0.25] (3), (q-q0) (12), dq*0.05 (12),
last action (12), sin/cos of the 0.8 s gait phase (2). Action: target = q0 + 0.25*action for the 12 leg joints.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

WEIGHTS = Path(__file__).parent / "assets" / "motion_weights.npz"


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


class LstmPolicy:
    def __init__(self, path: Path = WEIGHTS):
        w = np.load(path)
        self.w_ih, self.w_hh = w["memory.weight_ih_l0"], w["memory.weight_hh_l0"]
        self.b = w["memory.bias_ih_l0"] + w["memory.bias_hh_l0"]
        self.a0w, self.a0b, self.a2w, self.a2b = w["actor.0.weight"], w["actor.0.bias"], w["actor.2.weight"], w["actor.2.bias"]
        self.reset()

    def reset(self) -> None:
        self.h = np.zeros(64, np.float32)
        self.c = np.zeros(64, np.float32)

    def __call__(self, obs: np.ndarray) -> np.ndarray:
        z = self.w_ih @ obs + self.w_hh @ self.h + self.b
        i, f, g, o = np.split(z, 4)  # torch gate order: input, forget, cell, output
        self.c = _sigmoid(f) * self.c + _sigmoid(i) * np.tanh(g)
        self.h = _sigmoid(o) * np.tanh(self.c)
        x = self.a0w @ self.h + self.a0b
        x = np.where(x > 0, x, np.expm1(np.minimum(x, 0)))  # ELU
        return (self.a2w @ x + self.a2b).astype(np.float32)
