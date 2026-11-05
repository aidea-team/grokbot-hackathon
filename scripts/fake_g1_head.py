"""Fake G1 stereo head, to test the real-robot camera path without the robot.

Renders a simulator scene from two cameras 60 mm apart (like the custom head's module) and streams it the way the head's
g1-stereo-stream does, as far as src/g1/g1_real.py knows it: answers the {"magic":"G1ST","op":"hello"} UDP broadcast on port 5601
with a welcome, then sends side-by-side H.264 over RTP to the port in the hello, until the hellos stop.

  python scripts/fake_g1_head.py                     # stream (Ctrl+C to stop), slowly panning left and right
  python scripts/fake_g1_head.py --dump /tmp/pairs   # write a few left/right PNGs + ground-truth depth (.npy) and exit
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "g1"))
os.environ.setdefault("MUJOCO_GL", "cgl" if os.uname().sysname == "Darwin" else "egl")
import mujoco  # noqa: E402

from g1_world import SCENES  # noqa: E402


def _cam_quat(forward: np.ndarray) -> np.ndarray:
    """MuJoCo camera orientation (x right, y up, looking along -z) for a view direction with no roll."""
    f = forward / np.linalg.norm(forward)
    x = np.cross(f, [0, 0, 1.0])
    x /= np.linalg.norm(x)
    z = -f
    y = np.cross(z, x)
    q = np.zeros(4)
    mujoco.mju_mat2Quat(q, np.stack([x, y, z], axis=1).flatten())
    return q


class SimStereoHead:
    """Two fixed cameras in the world, `baseline` apart, at a robot-head height, pitched down; the robot itself is moved away."""

    def __init__(self, scene: str = "desk", eye: tuple[int, int] = (800, 600), hfov_deg: float = 75.0, baseline: float = 0.06,
                 height: float = 1.25, pitch_deg: float = 14.0, x: float = 0.1):
        self.eye, self.hfov, self.baseline, self.height, self.pitch, self.x = eye, hfov_deg, baseline, height, pitch_deg, x
        vfov = np.degrees(2 * np.arctan(np.tan(np.radians(hfov_deg) / 2) * eye[1] / eye[0]))
        spec = mujoco.MjSpec.from_file(str(SCENES[scene]))
        for name in ("stereo_l", "stereo_r"):
            spec.worldbody.add_camera(name=name, fovy=vfov)
        self.model = spec.compile()
        self.model.vis.global_.offwidth, self.model.vis.global_.offheight = max(1280, eye[0]), max(720, eye[1])
        self.data = mujoco.MjData(self.model)
        self.data.qpos[0] = -30.0  # the robot is far behind: we only want the room
        self._rgb = mujoco.Renderer(self.model, height=eye[1], width=eye[0])
        self._depth = mujoco.Renderer(self.model, height=eye[1], width=eye[0])
        self._depth.enable_depth_rendering()
        self.place(0.0)

    def place(self, yaw_deg: float, x: float | None = None, y: float = 0.0) -> None:
        yaw, pitch = np.radians(yaw_deg), np.radians(self.pitch)
        fwd = np.array([np.cos(pitch) * np.cos(yaw), np.cos(pitch) * np.sin(yaw), -np.sin(pitch)])
        left = np.array([-np.sin(yaw), np.cos(yaw), 0.0])
        centre = np.array([self.x if x is None else x, y, self.height])
        for name, side in (("stereo_l", 0.5), ("stereo_r", -0.5)):
            cid = self.model.camera(name).id
            self.model.cam_pos[cid] = centre + left * side * self.baseline
            self.model.cam_quat[cid] = _cam_quat(fwd)
        mujoco.mj_forward(self.model, self.data)

    def render(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(left RGB, right RGB, left ground-truth depth in m with NaN for the sky)."""
        out = []
        for name in ("stereo_l", "stereo_r"):
            self._rgb.update_scene(self.data, camera=name)
            out.append(self._rgb.render().copy())
        self._depth.update_scene(self.data, camera="stereo_l")
        z = self._depth.render().astype(np.float32)
        z[z >= 0.99 * self.model.vis.map.zfar * self.model.stat.extent] = np.nan
        return out[0], out[1], z


def stream(head: SimStereoHead, fps: int) -> None:
    w, h = head.eye
    welcome = json.dumps({"magic": "G1ST", "op": "welcome", "width": 2 * w, "height": h, "codec": "h264", "fps": fps}).encode()
    state = {"client": None, "hello": 0.0}

    def discovery() -> None:  # answers every hello; the latest sender (and its port) is where the video goes
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 5601))
        while True:
            data, addr = sock.recvfrom(2048)
            try:
                m = json.loads(data.decode())
            except ValueError:
                continue
            if m.get("magic") == "G1ST" and m.get("op") == "hello":
                sock.sendto(welcome, addr)
                state["client"], state["hello"] = (addr[0], int(m.get("port", 5600))), time.monotonic()

    threading.Thread(target=discovery, daemon=True, name="discovery").start()
    print(f"fake G1 head: waiting for a hello on UDP 5601 ({2 * w}x{h} side-by-side, {fps} fps, baseline {head.baseline * 1000:.0f} mm, "
          f"HFOV {head.hfov:.0f} deg)")
    ff, target, t0 = None, None, time.monotonic()
    try:
        while True:
            if time.monotonic() - state["hello"] > 6.0:  # the client is gone (it repeats the hello every 2 s)
                if ff:
                    ff.kill()
                    print("no more hellos: stream stopped")
                ff, target = None, None
                time.sleep(0.2)
                continue
            if state["client"] != target:
                if ff:
                    ff.kill()
                target = state["client"]
                ff = subprocess.Popen(
                    ["ffmpeg", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{2 * w}x{h}", "-r", str(fps),
                     "-i", "pipe:0", "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-g", str(fps),
                     "-x264-params", "repeat-headers=1", "-pix_fmt", "yuv420p", "-f", "rtp",
                     # own local ports: by default ffmpeg binds the destination port numbers, which on the same machine are the receiver's
                     f"rtp://{target[0]}:{target[1]}?localrtpport=15600&localrtcpport=15601"],
                    stdin=subprocess.PIPE)
                print(f"streaming to {target[0]}:{target[1]}")
            t = time.monotonic()
            head.place(25 * np.sin((t - t0) / 4))  # slow pan, +-25 deg
            left, right, _ = head.render()
            try:
                ff.stdin.write(np.concatenate([left, right], axis=1).tobytes())
            except BrokenPipeError:
                ff, target = None, None
            time.sleep(max(0.0, 1 / fps - (time.monotonic() - t)))
    except KeyboardInterrupt:
        pass
    finally:
        if ff:
            ff.kill()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scene", default="desk", choices=sorted(SCENES))
    ap.add_argument("--fps", type=int, default=10)
    ap.add_argument("--baseline", type=float, default=0.06, help="metres between the two cameras")
    ap.add_argument("--hfov", type=float, default=75.0, help="horizontal field of view of one eye, degrees")
    ap.add_argument("--dump", type=Path, help="write left/right/depth of a few views here and exit")
    args = ap.parse_args()
    head = SimStereoHead(args.scene, hfov_deg=args.hfov, baseline=args.baseline)
    if args.dump:
        from PIL import Image
        args.dump.mkdir(parents=True, exist_ok=True)
        for i, (yaw, x) in enumerate([(0, 0.1), (-15, 0.8), (10, 1.3)]):
            head.place(yaw, x)
            left, right, z = head.render()
            Image.fromarray(left).save(args.dump / f"{i}_left.png")
            Image.fromarray(right).save(args.dump / f"{i}_right.png")
            np.save(args.dump / f"{i}_depth.npy", z)
        print(f"wrote 3 views to {args.dump}")
        return 0
    stream(head, args.fps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
