"""Unitree Go2 drivers, same interface as the Go1 ones (src/dog/driver.py): connect / walk / strafe / primitive /
drive / stop / halt / close.

- Go2MockDriver: no network, integrates a 2D pose with the same timing as the real dog. Default everywhere.
- Go2Driver: sport-mode commands over WebRTC via `unitree_webrtc_connect` (pip install unitree_webrtc_connect,
  imported lazily: nothing here needs it until a human arms the real dog). See docs/hardware/robot-dog.md §1.2.

NOT VERIFIED ON A REAL GO2 (nobody has one yet; the museum dog is a Go1): the code follows the documented snippets
of docs/hardware/robot-dog.md. Things to check at the first human-supervised test are marked "VERIFY".

- WebRTC allows ONE client at a time: close the Unitree Go app first (RobotBusyError otherwise).
- Firmware >= 1.1.15 needs the owner's AES-128 key (GO2_AES_KEY in .env). Never commit it.
- `Move` is a velocity command and must be repeated: walk() sends it at 20 Hz and ends with StopMove.
- The kill switch is StopMove (halt() sends it immediately, from any thread). `Damp` is never sent.
- Tricks (Hello, Dance...) are one-shot: sent once, then we wait for them to finish.
"""
from __future__ import annotations

import asyncio
import io
import math
import os
import threading
import time

from driver import JsonlLog, MockDriver, WalkResult, _BaseDriver

# Go2 one-shot commands: primitive name -> (SPORT_CMD key, seconds we wait for it to finish). The waits are
# ESTIMATES (VERIFY at the first test): the dog finishes by itself, we only keep the mission loop from moving on.
PRIMITIVES: dict[str, tuple[str, float]] = {
    "stand_up": ("StandUp", 3.0),
    "lie_down": ("StandDown", 3.0),
    "recovery": ("RecoveryStand", 4.0),
    "sit": ("Sit", 3.0),
    "rise_sit": ("RiseSit", 3.0),
    "hello": ("Hello", 4.0),
    "stretch": ("Stretch", 5.0),
    "dance1": ("Dance1", 15.0),
    "dance2": ("Dance2", 15.0),
}
LOOP_DT = 0.05  # 20 Hz: the Move command is repeated at this rate
CAM_WIDTH = 480
CAM_FPS = 8


class _Go2Mixin:
    """What both Go2 drivers share on top of the Go1 base: strafing and one-shot primitives."""
    PRIMITIVES = PRIMITIVES
    LOOP_DT = LOOP_DT
    STOP_S = 0.3
    _vy = 0.0  # sideways velocity (m/s, +left) used by _send_velocity while a strafe runs

    def strafe(self, vy: float, seconds: float) -> WalkResult:
        """Sideways walk (+vy = left) for `seconds`, then stop. Same loop, halt handling and logging as walk()."""
        self.log.event("strafe_request", driver=self.name, vy=vy, seconds=seconds)
        self._vy = vy
        try:
            return self.walk(0.0, 0.0, seconds)
        finally:
            self._vy = 0.0

    def primitive(self, name: str, seconds: float | None = None) -> WalkResult:
        """One-shot sport command, then wait `seconds` (default from PRIMITIVES) for it to finish.
        halt() interrupts the wait and sends StopMove."""
        if name not in self.PRIMITIVES:
            return WalkResult(False, f"unknown primitive {name!r}")
        cmd, default_s = self.PRIMITIVES[name]
        seconds = default_s if seconds is None else seconds
        if not math.isfinite(seconds) or seconds <= 0:
            return WalkResult(False, f"seconds={seconds} must be a finite number > 0")
        self.log.event("primitive_request", driver=self.name, primitive=name, mode=cmd, seconds=seconds)
        if self.halt_event.is_set():
            return WalkResult(False, "halted")
        t0 = self.now()
        self._send_mode(cmd)
        while self.now() - t0 < seconds and not self.halt_event.is_set():
            self.sleep(self.LOOP_DT)
        interrupted = self.halt_event.is_set()
        if interrupted:
            self._send_idle()
        elapsed = self.now() - t0
        self.log.event("primitive_done", driver=self.name, primitive=name, elapsed_s=round(elapsed, 3),
                       interrupted=interrupted)
        return WalkResult(not interrupted, "halted" if interrupted else "ok", round(elapsed, 3), interrupted)


class Go2MockDriver(_Go2Mixin, MockDriver):
    name = "go2-mock"

    def connect(self) -> dict:
        info = {"model": "Go2 (mock)", "soc": 100}
        self.log.event("connect", driver=self.name, **info)
        return info

    def _integrate(self, vx: float, vyaw: float, vy: float = 0.0) -> None:
        now = time.monotonic()
        dt, self._last = now - self._last, now
        self.yaw += vyaw * dt
        self.x += (vx * math.cos(self.yaw) - vy * math.sin(self.yaw)) * dt
        self.y += (vx * math.sin(self.yaw) + vy * math.cos(self.yaw)) * dt

    def _send_velocity(self, vx: float, vyaw: float) -> None:
        self._integrate(vx, vyaw, self._vy)  # idle / stop ticks integrate nothing, even while a strafe is ending


# --------------------------------------------------------------------------------------------- camera
class Go2Camera:
    """Latest JPEG of the Go2 front camera, with the same small API as cams.CamRelay (acquire/release/frame)."""

    def __init__(self):
        self.cond = threading.Condition()
        self.frame: bytes | None = None
        self.frame_id = 0
        self.error: str | None = None
        self.viewers = 0  # frames are JPEG-encoded only while someone looks (or the agent holds it)
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            self.viewers += 1

    def release(self) -> None:
        with self._lock:
            self.viewers = max(0, self.viewers - 1)

    def publish(self, jpeg: bytes) -> None:
        with self.cond:
            self.frame, self.frame_id = jpeg, self.frame_id + 1
            self.cond.notify_all()

    def clear(self) -> None:
        with self.cond:
            self.frame = None

    def wait_frame(self, last_id: int, timeout: float = 2.0) -> tuple[int, bytes | None]:
        with self.cond:
            self.cond.wait_for(lambda: self.frame_id != last_id, timeout)
            return self.frame_id, self.frame


def mjpeg(camera):
    """Generator for a multipart/x-mixed-replace response (same format as cams.mjpeg)."""
    camera.acquire()
    last = 0
    try:
        while True:
            last, jpg = camera.wait_frame(last)
            if jpg is None:
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                   + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
    finally:
        camera.release()


class MockTopCamera:
    """Camera of the mock Go2: a synthetic top-down view (heading up, grid every 0.5 m, origin ring) drawn from the
    mock pose, so the whole chat loop can be tried without hardware. Not a simulation of what the dog would see."""

    def __init__(self, driver_getter):
        self._get = driver_getter
        self.error = None

    def acquire(self) -> None: ...
    def release(self) -> None: ...

    @property
    def frame(self) -> bytes:
        from PIL import Image, ImageDraw
        w, h, s = 480, 360, 90.0  # pixels, pixels, pixels per metre
        im = Image.new("RGB", (w, h), (18, 20, 28))
        d = ImageDraw.Draw(im)
        drv = self._get()
        x, y, yaw = (drv.x, drv.y, drv.yaw) if drv is not None else (0.0, 0.0, 0.0)
        c, sn = math.cos(yaw), math.sin(yaw)
        cx, cy = w / 2, h * 0.65

        def px(wx: float, wy: float) -> tuple[float, float]:
            rx, ry = wx - x, wy - y
            fwd, left = c * rx + sn * ry, -sn * rx + c * ry
            return cx - left * s, cy - fwd * s

        span = 5
        for i in range(-span, span + 1):
            for j in range(-span, span + 1):
                gx, gy = i * 0.5, j * 0.5
                p = px(gx, gy)
                if 0 <= p[0] < w and 0 <= p[1] < h:
                    d.line([(p[0] - 3, p[1]), (p[0] + 3, p[1])], fill=(60, 66, 84))
                    d.line([(p[0], p[1] - 3), (p[0], p[1] + 3)], fill=(60, 66, 84))
        o = px(0.0, 0.0)
        d.ellipse([o[0] - 8, o[1] - 8, o[0] + 8, o[1] + 8], outline=(120, 200, 140), width=2)
        d.polygon([(cx, cy - 26), (cx - 16, cy + 18), (cx + 16, cy + 18)], fill=(150, 120, 255))
        d.text((8, 6), "Go2 MOCK · vista dall'alto sintetica (non è una telecamera)", fill=(200, 200, 210))
        d.text((8, 22), f"x {x:.2f} m  y {y:.2f} m  yaw {math.degrees(yaw):.0f}°", fill=(200, 200, 210))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80)
        return buf.getvalue()


# --------------------------------------------------------------------------------------------- real link
class Go2Link:
    """The WebRTC connection to one Go2, run on its own asyncio loop in a background thread, with a blocking API.

    Lives for the whole app (the camera object is created once); connect() / disconnect() happen at arm / disarm.
    """

    def __init__(self, addr: str | None = None, aes_key: str | None = None):
        self.addr = addr or os.environ.get("GO2_ADDR") or os.environ.get("ROBOT_DOG_IP") or None
        self.aes_key = aes_key or os.environ.get("GO2_AES_KEY") or os.environ.get("ROBOT_DOG_AES_KEY") or None
        self.camera = Go2Camera()
        self.soc: int | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._conn = None
        self._sport_cmd: dict = {}
        self._topic: dict = {}
        self._pending = None  # last fire-and-forget Move/StopMove future: a new one is dropped while it is in flight
        self._last_jpeg = 0.0

    # --- loop plumbing
    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            loop = asyncio.new_event_loop()
            threading.Thread(target=loop.run_forever, daemon=True, name="go2-webrtc").start()
            self._loop = loop
        return self._loop

    def _run(self, coro, timeout: float):
        fut = asyncio.run_coroutine_threadsafe(coro, self._ensure_loop())
        try:
            return fut.result(timeout)
        except TimeoutError as e:
            fut.cancel()
            raise ConnectionError(f"timeout ({timeout:g} s) parlando col Go2") from e

    # --- connection
    def connect(self, timeout: float = 30.0) -> dict:
        info = self._run(self._connect(), timeout)
        deadline = time.monotonic() + 2.0
        while self.soc is None and time.monotonic() < deadline:  # battery arrives with the first low-state message
            time.sleep(0.1)
        return {"addr": self.addr or "192.168.12.1 (Wi-Fi del cane)", "soc": self.soc, **info}

    async def _connect(self) -> dict:
        try:
            from unitree_webrtc_connect.constants import RTC_TOPIC, SPORT_CMD
            from unitree_webrtc_connect.webrtc_driver import UnitreeWebRTCConnection, WebRTCConnectionMethod
        except ImportError as e:
            raise ConnectionError("unitree_webrtc_connect non installato: "
                                  ".venv/bin/pip install unitree_webrtc_connect") from e
        self._sport_cmd, self._topic = SPORT_CMD, RTC_TOPIC
        kw = {"aes_128_key": self.aes_key} if self.aes_key else {}
        try:
            if self.addr:  # LocalSTA: dog and PC on the same LAN
                conn = UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalSTA, ip=self.addr, **kw)
            else:  # LocalAP: the PC is on the dog's own Wi-Fi (192.168.12.1)
                conn = UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalAP, **kw)
            await conn.connect()
        except Exception as e:  # noqa: BLE001 - RobotBusyError, wrong key, no route...
            hint = " (chiudi l'app Unitree Go: un solo client alla volta)" if "usy" in type(e).__name__ else ""
            raise ConnectionError(f"{type(e).__name__}: {e}{hint}") from e
        self._conn = conn
        self.soc = None
        try:  # battery: VERIFY the topic/field names on the real dog
            def on_low_state(message):
                try:
                    self.soc = int(message["data"]["bms_state"]["soc"])
                except (KeyError, TypeError, ValueError):
                    pass
            conn.datachannel.pub_sub.subscribe(RTC_TOPIC["LOW_STATE"], on_low_state)
        except Exception:  # noqa: BLE001 - the battery is optional
            pass
        try:  # front camera: the video arrives as a WebRTC track
            conn.video.switchVideoChannel(True)
            conn.video.add_track_callback(self._on_track)
        except Exception as e:  # noqa: BLE001 - the dog can be driven without the camera
            self.camera.error = f"{type(e).__name__}: {e}"
        return {"model": "Go2"}

    async def _on_track(self, track) -> None:
        interval = 1.0 / CAM_FPS
        while self._conn is not None:
            try:
                frame = await track.recv()
            except Exception as e:  # noqa: BLE001 - track closed
                self.camera.error = f"{type(e).__name__}: {e}"
                return
            now = time.monotonic()
            if self.camera.viewers <= 0 or now - self._last_jpeg < interval:
                continue  # encoding every frame would waste CPU; only while someone looks
            self._last_jpeg = now
            try:
                img = frame.to_image()
                img = img.resize((CAM_WIDTH, max(1, round(img.height * CAM_WIDTH / img.width))))
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=70)
                self.camera.error = None
                self.camera.publish(buf.getvalue())
            except Exception as e:  # noqa: BLE001
                self.camera.error = f"{type(e).__name__}: {e}"

    def disconnect(self) -> None:
        conn, self._conn = self._conn, None
        self.camera.clear()
        if conn is None or self._loop is None:
            return
        try:
            self._run(conn.disconnect(), 5.0)
        except Exception:  # noqa: BLE001 - closing: nothing more to do
            pass

    # --- commands
    async def _sport(self, name: str, parameter=None):
        payload = {"api_id": self._sport_cmd[name]}
        if parameter is not None:
            payload["parameter"] = parameter
        resp = await self._conn.datachannel.pub_sub.publish_request_new(self._topic["SPORT_MOD"], payload)
        return resp["data"]["header"]["status"]["code"]  # 0 = ok

    def sport(self, name: str, parameter=None, timeout: float = 5.0):
        """Blocking one-shot sport command. Returns the status code (0 = ok). Raises ConnectionError if not connected."""
        if self._conn is None:
            raise ConnectionError("Go2 non connesso")
        return self._run(self._sport(name, parameter), timeout)

    def _fire(self, name: str, parameter=None) -> None:
        """Fire-and-forget (velocity streaming and the kill switch): never blocks; a Move is dropped while the
        previous one is still in flight, StopMove always goes."""
        if self._conn is None or self._loop is None:
            return
        if name == "Move" and self._pending is not None and not self._pending.done():
            return
        self._pending = asyncio.run_coroutine_threadsafe(self._sport(name, parameter), self._loop)

    def move(self, vx: float, vy: float, vyaw: float) -> None:
        self._fire("Move", {"x": vx, "y": vy, "z": vyaw})  # VERIFY: z > 0 = turn left (ROS convention)

    def stop_move(self) -> None:
        self._fire("StopMove")


class Go2Driver(_Go2Mixin, _BaseDriver):
    name = "go2"

    def __init__(self, log: JsonlLog, link: Go2Link | None = None):
        super().__init__(log)
        self.link = link or Go2Link()
        self._balanced = False  # Move needs the dog in BalanceStand after a posture command (VERIFY)

    def connect(self) -> dict:
        try:
            info = self.link.connect()
        except ConnectionError:
            self.log.event("connect_failed", driver=self.name, addr=self.link.addr)
            raise
        self.log.event("connect", driver=self.name, **info)
        return info

    def halt(self) -> None:
        """Kill switch: set the flag AND send StopMove right now (from any thread), without waiting for the loop."""
        super().halt()
        self.link.stop_move()

    def _ensure_balanced(self) -> None:
        if not self._balanced:
            self.link.sport("BalanceStand")
            self.sleep(0.3)
            self._balanced = True

    def walk(self, vx: float, vyaw: float, seconds: float) -> WalkResult:
        self._ensure_balanced()  # before the timed loop, so BalanceStand does not eat into the walk time
        return super().walk(vx, vyaw, seconds)

    def _send_velocity(self, vx: float, vyaw: float) -> None:
        self._ensure_balanced()  # teleop ticks arrive here directly through drive()
        self.link.move(vx, self._vy, vyaw)

    def _send_idle(self) -> None:
        self.link.stop_move()  # never Damp

    def _send_mode(self, mode: str) -> None:
        self._balanced = False
        self.link.sport(mode)

    def close(self) -> None:
        self.stop()
        self.link.disconnect()
        self.log.event("close", driver=self.name)
