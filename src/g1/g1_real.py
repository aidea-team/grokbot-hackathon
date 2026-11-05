"""RealG1: the REAL Unitree G1 through the robot's own HIGH-LEVEL services only.

What we send (all high level, all the robot's own controller does the balancing): LocoClient.Move/StopMove (walking), SetFsmId for a
short whitelist of modes (Start, walking 501, Sit, Squat<->Stand: NOT Damp, NOT Lie2StandUp), HighStand/LowStand, SetBalanceMode, WaveHand,
and the arm-action service (ExecuteAction: the 16 built-in gestures). Plus reads (GetFsmId).
What we NEVER send: developer mode or any mode switch of the control service (MotionSwitcher / SwitchToUserCtrl / SelectMode / ReleaseMode),
low-level commands (rt/lowcmd, rt/arm_sdk: a controller that sends nothing or wrong values to the motors in developer mode is equivalent
to zero torque = damp, the robot falls), zero-torque. Joint-level arm jog needs rt/arm_sdk (low level), so it is refused here.

A human or the agent may launch it (CLAUDE.md); the browser must still confirm ("arm"). Camera: the custom head's stereo streamer
(UDP discovery + RTP H.264), independent of the robot link. State machine like the dog's RealBody: DISARMED -> ARMED -> HALTED.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import numpy as np

from g1_world import ARM_ACTION_IDS, UPPER

DISARMED, ARMED, HALTED = "disarmed", "armed", "halted"
WATCHDOG_S = 0.4
ARM_API_EXECUTE_CUSTOM, ARM_API_STOP_CUSTOM = 7108, 7113  # unitree_sdk2 C++ g1_arm_action_api.hpp
# Real robot velocity ceilings (env override on purpose). The UI default stays low: you raise it with the slider.
REAL_MAX_VX = float(os.environ.get("G1_REAL_MAX_VX", 1.0))
REAL_MAX_VY = float(os.environ.get("G1_REAL_MAX_VY", 0.4))
REAL_MAX_VYAW = float(os.environ.get("G1_REAL_MAX_VYAW", 1.0))
# FSM ids we may request (SDK: 3 Sit, 500 Start, 706 Squat<->StandUp; 501 = walking per third-party sources, VERIFY).
# NOT allowed, on purpose: 1 (Damp: the robot goes limp and sags), 702 (Lie2StandUp: can damage it unless it lies face up on hard flat ground),
# 0 (zero torque), anything else. Stopping = StopMove; the real emergency stop is the remote.
ALLOWED_FSM = {3: "Sit", 500: "Start", 501: "modalità camminata", 706: "Squat <-> StandUp"}



DDS_PEERS = os.environ.get("G1_DDS_PEERS", "192.168.123.161,192.168.123.164").split(",")


def configure_dds(iface: str | None) -> None:
    """OPTIONAL unicast DDS discovery (G1_DDS_UNICAST=1, peers in G1_DDS_PEERS). The real cause of the Mac's RPC timeouts was the
    Python CycloneDDS version (11.x on the Mac vs 0.10.x on the robot): with cyclonedds==0.10.2 the SDK's default config works."""
    if os.environ.get("G1_DDS_UNICAST") != "1":
        return  # default: the SDK's own config. With CycloneDDS 0.10.x (same series as the robot) multicast discovery works, also on
        #         Wi-Fi; our unicast-only config made discovery FAIL there (tested 2026-11-04). Opt-in only: G1_DDS_UNICAST=1.
    import unitree_sdk2py.core.channel as ch
    import unitree_sdk2py.core.channel_config as cc
    peers = "".join(f'<Peer address="{a.strip()}"/>' for a in DDS_PEERS if a.strip())
    cfg = f"""<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS><Domain Id="any">
  <General>{'<Interfaces><NetworkInterface name="$__IF_NAME__$" priority="default" multicast="false"/></Interfaces>' if iface else ''}<AllowMulticast>false</AllowMulticast></General>
  <Discovery><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>120</MaxAutoParticipantIndex><Peers>{peers}</Peers></Discovery>
</Domain></CycloneDDS>"""
    for mod in (cc, ch):  # channel.py imported the names already: patch both
        if iface:
            mod.ChannelConfigHasInterface = cfg
        mod.ChannelConfigAutoDetermine = cfg

ACTIONS_CACHE = Path(__file__).parent / "assets" / "arm_actions_robot.json"  # the robot's own list, saved the first time we read it


def _slug(name: str, ident: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    return slug or f"action_{ident}"


def parse_action_list(data) -> dict[str, int]:
    """Robot reply of G1ArmActionClient.GetActionList -> {slug: id}. The exact format is not documented, so accept the plausible ones:
    a list of {id/action_id, name/action_name} dicts, a {name: id} or {id: name} dict, optionally wrapped under data/actions/action_list."""
    out: dict[str, int] = {}

    def add(name, ident) -> None:
        try:
            i = int(ident)
        except (TypeError, ValueError):
            return
        if name is not None and str(name).strip() != "":
            out[_slug(str(name), i)] = i

    items = data
    if isinstance(data, dict):
        for key in ("data", "actions", "action_list", "list"):
            if key in data:
                items = data[key]
                break
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except ValueError:
            return out
    if isinstance(items, dict):
        for k, v in items.items():
            if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
                add(k, v)
            elif str(k).isdigit():
                add(v, k)
    elif isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                name = next((it[k] for k in ("name", "action_name", "title", "label") if k in it), None)
                ident = next((it[k] for k in ("id", "action_id", "index", "code") if k in it), None)
                add(name, ident)
    return out


def parse_action_groups(data) -> tuple[dict[str, int], list[dict]]:
    """Real reply of GetActionList on this G1 (checked 2026-11-04): [[{id, name}, ...built-in...], [{name, time}, ...taught in the app...]].
    Returns ({slug: id} of the built-in actions, [{name, time}] of the taught ones). Other shapes fall back to parse_action_list."""
    if isinstance(data, list) and data and all(isinstance(g, list) for g in data):
        builtin: dict[str, int] = {}
        custom: list[dict] = []
        for group in data:
            for it in group:
                if not isinstance(it, dict) or it.get("name") in (None, ""):
                    continue
                if it.get("id") is not None:
                    try:
                        builtin[_slug(it["name"], int(it["id"]))] = int(it["id"])
                    except (TypeError, ValueError):
                        pass
                else:
                    custom.append({"name": str(it["name"]), "time": it.get("time")})
        return builtin, custom
    return parse_action_list(data), []


def load_cached_custom() -> list[dict]:
    try:
        return [c for c in json.loads(ACTIONS_CACHE.read_text()).get("custom", []) if isinstance(c, dict) and c.get("name")]
    except (OSError, ValueError, AttributeError):
        return []


def load_cached_actions() -> dict[str, int]:
    """The robot's action list as last read (for the mock's gesture list); empty if we never read it."""
    try:
        return {str(k): int(v) for k, v in json.loads(ACTIONS_CACHE.read_text()).get("actions", {}).items()}
    except (OSError, ValueError, AttributeError):
        return {}


class RealError(Exception):
    pass


class _Camera:
    """The G1's head camera, read-only, only while someone watches.

    Default: the custom head's stereo streamer (repo g1-stereo-stream on the head PC, Intel N150): we announce ourselves with a
    UDP broadcast {"magic":"G1ST","op":"hello","port":5600} on port 5601, it answers with a welcome (size/codec/fps) and sends
    H.264 over RTP to us (3200x1200@60, side-by-side stereo); we repeat the hello every 2 s as heartbeat. ffmpeg decodes it and we
    keep the LEFT eye as JPEG. Override with G1_CAMERA_URL (anything ffmpeg can read: rtsp://, udp://, http mjpeg).
    """
    DISCOVERY_PORT, VIDEO_PORT, HEARTBEAT_S = 5601, 5600, 2.0

    def __init__(self, url: str | None = None, fps: int = 10, width: int = 640):
        self.url, self.fps, self.width = url, fps, width
        self.cond = threading.Condition()
        self.jpeg: bytes | None = None
        self.n = 0
        self.error: str | None = "in attesa della camera…"
        self.info: dict | None = None
        self._seen = 0.0
        self._running = False
        self._lock = threading.Lock()

    def get(self, after: int = -1, timeout: float = 2.0) -> tuple[int, bytes | None]:
        self._seen = time.monotonic()
        if not self._running:
            with self._lock:
                if not self._running:
                    self._running = True
                    threading.Thread(target=self._run, daemon=True, name="g1-cam").start()
        with self.cond:
            self.cond.wait_for(lambda: self.n > after, timeout)
            return self.n, self.jpeg

    def _discover(self, timeout: float = 6.0) -> dict | None:
        import json
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.5)
        hello = json.dumps({"magic": "G1ST", "op": "hello", "port": self.VIDEO_PORT}).encode()
        t = time.monotonic()
        try:
            while time.monotonic() - t < timeout and time.monotonic() - self._seen < 5.0:
                for dst in ("255.255.255.255", "192.168.123.255"):
                    try:
                        sock.sendto(hello, (dst, self.DISCOVERY_PORT))
                    except OSError:
                        pass
                try:
                    data, addr = sock.recvfrom(2048)
                    m = json.loads(data.decode())
                    if m.get("magic") == "G1ST" and m.get("op") == "welcome":
                        m["server"] = addr[0]
                        return m
                except (TimeoutError, ValueError):
                    pass
        finally:
            sock.close()
        return None

    def _heartbeat(self, server: str, stop: threading.Event) -> None:
        import json
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        hello = json.dumps({"magic": "G1ST", "op": "hello", "port": self.VIDEO_PORT}).encode()
        while not stop.wait(self.HEARTBEAT_S):
            try:
                sock.sendto(hello, (server, self.DISCOVERY_PORT))
            except OSError:
                pass
        sock.close()

    def _ffmpeg(self, sdp_path: str | None) -> subprocess.Popen:
        vf = f"fps={self.fps},scale={self.width}:-2,format=yuvj420p"
        if sdp_path:  # stereo side-by-side: keep the left eye
            src = ["-protocol_whitelist", "file,udp,rtp", "-buffer_size", "8388608", "-fflags", "nobuffer", "-flags", "low_delay", "-i", sdp_path]
            vf = f"crop=iw/2:ih:0:0,{vf}"
        else:
            src = ["-fflags", "nobuffer", "-flags", "low_delay", "-i", self.url]
        return subprocess.Popen(["ffmpeg", "-loglevel", "error", *src, "-vf", vf, "-q:v", "5", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def _run(self) -> None:
        import tempfile
        stop = threading.Event()
        try:
            while time.monotonic() - self._seen < 5.0:
                sdp_path = None
                if self.url is None:
                    self.error = "cerco lo streamer stereo della testa (broadcast UDP 5601)…"
                    welcome = self._discover()
                    if welcome is None:
                        self.error = "nessuno streamer stereo trovato: la testa è accesa e lo streaming avviato?"
                        time.sleep(1)
                        continue
                    self.info = welcome
                    stop = threading.Event()
                    threading.Thread(target=self._heartbeat, args=(welcome["server"], stop), daemon=True, name="g1-cam-hb").start()
                    codec = "H265" if welcome.get("codec") == "h265" else "H264"
                    f = tempfile.NamedTemporaryFile("w", suffix=".sdp", delete=False)
                    f.write(f"v=0\no=- 0 0 IN IP4 127.0.0.1\ns=g1\nc=IN IP4 0.0.0.0\nt=0 0\n"
                            f"m=video {self.VIDEO_PORT} RTP/AVP 96\na=rtpmap:96 {codec}/90000\n")
                    f.close()
                    sdp_path = f.name
                try:
                    ff = self._ffmpeg(sdp_path)
                except FileNotFoundError:
                    self.error = "ffmpeg non trovato (brew install ffmpeg)"
                    return
                buf, got, last = b"", False, time.monotonic()
                started = time.monotonic()  # the first frames are decoded without a keyframe (grey garbage): skip them
                while time.monotonic() - self._seen < 5.0 and time.monotonic() - last < 8.0:
                    chunk = ff.stdout.read1(65536)
                    if not chunk:
                        break
                    buf += chunk
                    while True:
                        a = buf.find(b"\xff\xd8")
                        e = buf.find(b"\xff\xd9", a + 2) if a >= 0 else -1
                        if a < 0 or e < 0:
                            break
                        jpg, buf = buf[a:e + 2], buf[e + 2:]
                        if sdp_path and time.monotonic() - started < 2.0:
                            continue
                        got, last, self.error = True, time.monotonic(), None
                        with self.cond:
                            self.jpeg, self.n = jpg, self.n + 1
                            self.cond.notify_all()
                ff.kill()
                stop.set()
                if not got:
                    self.error = "nessun video dalla camera del robot"
                    time.sleep(1)
        finally:
            stop.set()
            self._running = False


class RealG1:
    name = "real"
    FSM_WAIT_S = 1.5  # wait before reading the FSM back after a mode request
    REFUSAL = ("not enabled on the real robot: single-joint arm control needs the low level, "
               "which we never send. Use gestures (SDK actions).")

    def __init__(self, iface: str | None = None, camera_url: str | None = None, log=None, limits=None):
        self.iface = iface or os.environ.get("G1_IFACE") or None
        self.log = log
        self.state = DISARMED
        self.camera = _Camera(camera_url or os.environ.get("G1_CAMERA_URL") or None)
        self._loco = None
        self._arm_client = None
        self._busy_until = 0.0
        self.actions: dict[str, int] = dict(ARM_ACTION_IDS)  # replaced by the robot's own list when arm() can read it
        self.actions_source = "tabella dell'SDK (non letta dal robot)"
        self.custom_actions: list[dict] = []  # taught in the Unitree app: [{name, time}], run by NAME (API 7108), no id
        self._cmd = (0.0, 0.0, 0.0)
        self._cmd_t = 0.0
        self._moving = False
        self._fsm: int | None = None
        self._fsm_code: int | None = None
        self._stop = False
        self._watchdog: threading.Thread | None = None

    # ------------------------------------------------------------------ life cycle
    def _ev(self, kind: str, **f) -> None:
        if self.log is not None:
            self.log.event(kind, robot="g1", **f)

    def arm(self) -> None:
        """Connect the locomotion client. Sends nothing that moves or changes mode (only a GetFsmId read)."""
        try:
            from unitree_sdk2py.core.channel import ChannelFactoryInitialize
            from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
        except ImportError as e:  # pragma: no cover - needs the SDK
            raise RealError("unitree_sdk2py is missing (needs the Unitree SDK and cyclonedds)") from e
        try:
            configure_dds(self.iface)
            ChannelFactoryInitialize(0, self.iface) if self.iface else ChannelFactoryInitialize(0)
            self._loco = LocoClient()
            self._loco.SetTimeout(5.0)
            self._loco.Init()
            try:  # gestures: the arm-action service; if it is not there, walking and modes still work
                from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient
                self._arm_client = G1ArmActionClient()
                self._arm_client.SetTimeout(10.0)
                self._arm_client.Init()
                self._arm_client._RegistApi(ARM_API_EXECUTE_CUSTOM, 0)  # documented in the robot's C++ SDK, missing from the Python one
                self._arm_client._RegistApi(ARM_API_STOP_CUSTOM, 0)
            except Exception as e:  # noqa: BLE001
                self._arm_client = None
                self._ev("g1_arm_client_unavailable", error=str(e))
            else:
                self._load_actions()
            code, fsm = self._loco.GetFsmId()  # informational only: it never blocks arming
        except Exception as e:  # noqa: BLE001
            raise RealError(f"connection to the G1 failed: {e}") from e
        self._fsm, self._fsm_code = (fsm if code == 0 else None), code
        self._stop = False
        if self._watchdog is None:
            self._watchdog = threading.Thread(target=self._watchdog_loop, daemon=True, name="g1-watchdog")
            self._watchdog.start()
        self.state = ARMED
        self._ev("g1_arm", fsm=self._fsm, fsm_code=code)

    def disarm(self) -> None:
        if self.state == ARMED:
            self._stop_move()
        self.state = DISARMED

    def kill(self, source: str = "?") -> None:
        """Independent of the model: StopMove (a velocity of zero, nothing else) and latch HALTED."""
        self.state = HALTED
        self._cmd, self._moving = (0.0, 0.0, 0.0), False
        try:
            if self._loco is not None:
                self._loco.StopMove()
        except Exception:  # noqa: BLE001
            pass
        self.stop_custom()
        self._ev("g1_kill", source=source)

    def shutdown(self) -> None:
        self._stop = True
        self.kill("shutdown")

    def heartbeat(self) -> None:
        pass

    # ------------------------------------------------------------------ the only things that reach the robot
    def _need_armed(self) -> None:
        if self.state != ARMED or self._loco is None:
            raise RealError(f"real robot not armed (state: {self.state})")

    def _stop_move(self) -> None:
        self._cmd, self._moving = (0.0, 0.0, 0.0), False
        try:
            if self._loco is not None:
                self._loco.StopMove()
        except Exception:  # noqa: BLE001
            pass

    def command(self, vx: float, vy: float, vyaw: float) -> None:
        """LocoClient.Move: the robot's own walking controller. continuous_move=False: it stops by itself 1 s after the last call."""
        self._need_armed()
        c = (float(np.clip(vx, -REAL_MAX_VX, REAL_MAX_VX)), float(np.clip(vy, -REAL_MAX_VY, REAL_MAX_VY)),
             float(np.clip(vyaw, -REAL_MAX_VYAW, REAL_MAX_VYAW)))
        self._cmd, self._cmd_t, self._moving = c, time.monotonic(), True
        code = self._loco.Move(*c)
        if isinstance(code, int) and code != 0:
            raise RealError(f"the robot refused Move (code {code}): it is probably not in normal/walking mode")

    def stop(self) -> None:
        if self.state == ARMED:
            self._stop_move()

    def _watchdog_loop(self) -> None:
        while not self._stop:
            time.sleep(0.1)
            if self._moving and time.monotonic() - self._cmd_t > WATCHDOG_S and self.state == ARMED:
                self._stop_move()

    # ------------------------------------------------------------------ modes, stand, gestures (all high level)
    def set_fsm(self, fsm_id: int) -> dict:
        """LocoClient.SetFsmId for a whitelisted id; waits and reads the FSM back so the human sees whether the robot really changed."""
        self._need_armed()
        if fsm_id not in ALLOWED_FSM:
            raise RealError(f"FSM {fsm_id} not allowed (allowed: {sorted(ALLOWED_FSM)})")
        self._stop_move()
        code = self._loco.SetFsmId(fsm_id)
        time.sleep(self.FSM_WAIT_S)
        c2, now = self._loco.GetFsmId()
        if c2 == 0:
            self._fsm = now
        self._ev("g1_fsm", requested=fsm_id, code=code, after=now if c2 == 0 else None)
        return {"requested": fsm_id, "code": code, "fsm": now if c2 == 0 else None, "changed": c2 == 0 and now == fsm_id}

    def damp(self):
        """Damp (motors limp, the robot sags) is deliberately not available on the real robot."""
        raise RealError("Damp is not available on the real robot (it makes it sag): use STOP or the remote to halt it")

    def reset(self) -> dict:
        """LocoClient.Start(): FSM 500."""
        return self.set_fsm(500)

    def stand_height(self, high: bool) -> bool:
        self._need_armed()
        self._loco.HighStand() if high else self._loco.LowStand()
        self._ev("g1_stand_height", high=high)
        return True

    def balance_mode(self, mode: int) -> bool:
        self._need_armed()
        if mode not in (0, 1):
            raise RealError("balance mode must be 0 or 1")
        self._loco.SetBalanceMode(mode)
        self._ev("g1_balance_mode", mode=mode)
        return True

    def _load_actions(self, cache: Path | None = ACTIONS_CACHE) -> None:
        """Ask the robot which arm actions it really has (GetActionList: a read). Falls back to the SDK's example table."""
        try:
            code, data = self._arm_client.GetActionList()
        except Exception as e:  # noqa: BLE001
            self._ev("g1_action_list_error", error=str(e))
            return
        self._ev("g1_action_list", code=code, raw=json.dumps(data, ensure_ascii=False)[:4000])  # keep the raw reply: the format is undocumented
        found, custom = parse_action_groups(data) if code == 0 else ({}, [])
        if found or custom:
            self.custom_actions = custom
        if found:
            self.actions, self.actions_source = found, "robot"
            if cache is not None:
                try:
                    cache.write_text(json.dumps({"source": "robot", "actions": found, "custom": self.custom_actions}, ensure_ascii=False, indent=1))
                except OSError:
                    pass

    def gesture_names(self) -> list[str]:
        """Everything this robot can do with its arms that we may trigger: its own action list + WaveHand."""
        names = [n for n in self.actions if n != "release_arm"]
        return names + [n for n in ("wave_hand", "wave_hand_turn") if n not in names]

    def play(self, name: str) -> bool:
        """Gestures: LocoClient.WaveHand, or one of the robot's own arm actions by id (G1ArmActionClient.ExecuteAction)."""
        self._need_armed()
        if name in ("wave_hand", "wave_hand_turn") or name in self.actions:
            self._stop_move()  # arms move only when the robot is still (and it ignores Move while they move): stop first
            time.sleep(0.3)
        self._ev("g1_gesture", name=name)
        if name in ("wave_hand", "wave_hand_turn"):
            self._busy_until = time.monotonic() + 8.0
            self._loco.WaveHand(name == "wave_hand_turn")
            return True
        if name in self.actions:
            if self._arm_client is None:
                raise RealError("the arm actions service does not respond")
            self._busy_until = time.monotonic() + 8.0
            self._arm_client.ExecuteAction(self.actions[name])
            return True
        return False

    def play_custom(self, name: str) -> bool:
        """A move taught in the Unitree app, by its exact name (arm service API 7108). Only names the robot itself listed."""
        self._need_armed()
        if name not in {c["name"] for c in self.custom_actions}:
            return False
        self._stop_move()
        time.sleep(0.3)
        self._ev("g1_custom_action", name=name)
        self._busy_until = time.monotonic() + 12.0
        code, _ = self._arm_client._Call(ARM_API_EXECUTE_CUSTOM, json.dumps({"action_name": name}))
        if code != 0:
            raise RealError(f"the robot refused the action “{name}” (code {code})")
        return True

    def stop_custom(self) -> None:
        """Best effort: stop a taught move in progress (arm service API 7113). Safe to call any time."""
        try:
            if self._arm_client is not None:
                self._arm_client._Call(ARM_API_STOP_CUSTOM, "{}")
        except Exception:  # noqa: BLE001
            pass

    def agent_gestures(self) -> list[str]:
        """What the CHAT may trigger by itself: only the actions of the SDK's own table (the ones Unitree documents). The extra built-in ones
        are not in the Unitree app and per Unitree's header 'may cause the robot to fall'; taught moves are never offered to the model.
        G1_AGENT_ALL_GESTURES=1 offers every built-in action."""
        if os.environ.get("G1_AGENT_ALL_GESTURES") == "1":
            return self.gesture_names()
        known = set(ARM_ACTION_IDS.values())
        return [n for n, i in self.actions.items() if i in known and n != "release_arm"] + ["wave_hand", "wave_hand_turn"]

    def is_busy(self) -> bool:
        return time.monotonic() < self._busy_until

    # joint-level arm control = low level (rt/arm_sdk): refused
    def jog(self, rates):
        raise RealError(self.REFUSAL)

    def set_pose(self, pose):
        raise RealError(self.REFUSAL)

    # ------------------------------------------------------------------ views
    def snapshot(self) -> dict:
        return {"robot": "g1", "mode": "real", "state": self.state, "fsm": self._fsm, "fsm_rpc_code": self._fsm_code,
                "vx": round(self._cmd[0], 2), "vy": round(self._cmd[1], 2), "vyaw": round(self._cmd[2], 2),
                "fallen": False, "falls": 0, "preset": "in corso" if self.is_busy() else None, "damped": self._fsm == 1,
                "arms": {}, "camera_error": self.camera.error}

    def frame(self, after: int = -1, timeout: float = 2.0, view: str = "head") -> tuple[int, bytes | None]:
        return self.camera.get(after, timeout)

    def head_jpeg(self, timeout: float = 3.0) -> bytes | None:
        n, _ = self.camera.get(-1, 0.1)
        return self.camera.get(n, timeout)[1]
