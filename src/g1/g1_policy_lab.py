"""Unitree's G1 29-DoF velocity policy from unitree_rl_lab (deploy/robots/g1_29dof/config/policy/velocity/v0), run with onnxruntime.

Unlike the older unitree_rl_gym policy (g1_policy.py: 12 leg joints, arms fixed forward at 90 deg), this one drives ALL 29 joints, arms and waist
included, from the default pose below (elbows ~55 deg, shoulders slightly forward and out). Everything here follows Unitree's own deploy code
(vendor reference: unitree_rl_lab/deploy/include/isaaclab/*, State_RLBase.cpp, unitree_articulation.h):

- policy joint order = Isaac Lab breadth-first order; `JOINT_IDS_MAP[i]` is the robot motor index (G1JointIndex, 0..28) of policy joint i
- observation, per step: base_ang_vel * 0.2 (pelvis gyro), projected_gravity (R^T (0,0,-1)), velocity_commands, joint_pos_rel,
  joint_vel_rel * 0.05, last_action (raw); each TERM keeps a 5-step history (oldest first) and terms are concatenated: 5*(3+3+3+29+29+29) = 480
- the history is initialised by repeating the first observation
- target position of motor JOINT_IDS_MAP[i] = DEFAULT[i] + 0.25 * action[i]; PD gains in robot MOTOR order (STIFFNESS / DAMPING)
- 50 Hz; command ranges of the deploy config: x [-0.5, 1.0], y [-0.3, 0.3], yaw [-0.2, 0.2]
The weights are Unitree's (see assets/lab29/); check their license before redistributing outside the team.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

ASSETS = Path(__file__).parent / "assets" / "lab29"

JOINT_IDS_MAP = np.array([0, 6, 12, 1, 7, 13, 2, 8, 14, 3, 9, 15, 22, 4, 10, 16, 23, 5, 11, 17, 24, 18, 25, 19, 26, 20, 27, 21, 28])
# policy order (breadth first): L/R hip pitch, waist yaw, hip roll L/R, waist roll, hip yaw L/R, waist pitch, knee L/R, shoulder pitch L/R,
# ankle pitch L/R, shoulder roll L/R, ankle roll L/R, shoulder yaw L/R, elbow L/R, wrist roll L/R, wrist pitch L/R, wrist yaw L/R
DEFAULT = np.array([-0.1, -0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.3, 0.3, 0.3, -0.2, -0.2, 0.25, -0.25, 0.0, 0.0, 0.0, 0.0,
                    0.97, 0.97, 0.15, -0.15, 0.0, 0.0, 0.0, 0.0], np.float32)
# gains in robot MOTOR order (legs 0-11, waist 12-14, arms 15-28), as the deploy code writes them to motor_cmd[i]
STIFFNESS = np.array([100, 100, 100, 150, 40, 40, 100, 100, 100, 150, 40, 40, 200, 200, 200] + [40] * 14, np.float32)
DAMPING = np.array([2, 2, 2, 4, 2, 2, 2, 2, 2, 4, 2, 2, 5, 5, 5] + [10] * 14, np.float32)
ACTION_SCALE = 0.25
ANG_VEL_SCALE, JOINT_VEL_SCALE = 0.2, 0.05
HISTORY = 5
CMD_LIMITS = (np.array([-0.5, -0.3, -0.2], np.float32), np.array([1.0, 0.3, 0.2], np.float32))  # (low, high) of (vx, vy, vyaw)
STEP_DT = 0.02


class LabPolicy:
    def __init__(self, path: Path = ASSETS / "policy.onnx"):
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), sess_options=opts, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.reset()

    def reset(self) -> None:
        self.last_action = np.zeros(29, np.float32)
        self._hist: list[list[np.ndarray]] | None = None  # per term: list of the last HISTORY observations (oldest first)

    def observe(self, ang_vel_b: np.ndarray, gravity_proj_b: np.ndarray, cmd: np.ndarray, q_motor: np.ndarray, dq_motor: np.ndarray) -> np.ndarray:
        """q_motor/dq_motor: the 29 robot joints in motor order (qpos[7:36], qvel[6:35])."""
        terms = [
            ang_vel_b * ANG_VEL_SCALE,
            gravity_proj_b,
            np.clip(cmd, *CMD_LIMITS),
            q_motor[JOINT_IDS_MAP] - DEFAULT,
            dq_motor[JOINT_IDS_MAP] * JOINT_VEL_SCALE,
            self.last_action,
        ]
        terms = [np.asarray(t, np.float32) for t in terms]
        if self._hist is None:  # reset: the first observation fills the history
            self._hist = [[t.copy() for _ in range(HISTORY)] for t in terms]
        else:
            for h, t in zip(self._hist, terms):
                h.pop(0)
                h.append(t)
        return np.concatenate([np.concatenate(h) for h in self._hist]).astype(np.float32)

    def act(self, obs: np.ndarray) -> np.ndarray:
        """Raw action (policy order). Returns the motor-order position targets via `targets()`."""
        self.last_action = self.session.run(None, {self.input_name: obs[None, :]})[0][0].astype(np.float32)
        return self.last_action

    def targets(self, action: np.ndarray | None = None) -> np.ndarray:
        """Position targets for the 29 motors, in motor order."""
        a = self.last_action if action is None else action
        out = np.zeros(29, np.float32)
        out[JOINT_IDS_MAP] = DEFAULT + ACTION_SCALE * a
        return out

    @staticmethod
    def default_targets() -> np.ndarray:
        out = np.zeros(29, np.float32)
        out[JOINT_IDS_MAP] = DEFAULT
        return out
