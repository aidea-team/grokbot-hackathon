"""Go1 cameras -> MJPEG for the browser. Read-only: nothing is installed or started on the dog.

The dog's own web app (http://<dog>/) serves each camera as a WebSocket `ws://<dog>/cam1..cam5`
carrying H.264 (Annex B). The client must send an Int32 frame counter every ~500 ms. We read that,
pipe it through ffmpeg (brew install ffmpeg) and keep the latest JPEG for /cam/<n>.mjpg.
A relay runs only while someone is watching.
"""
from __future__ import annotations

import os
import struct
import subprocess
import threading
import time

DOG_HOST = os.environ.get("GO1_ADDR", "192.168.12.1")
IDLE_STOP_S = 5.0


class CamRelay:
    def __init__(self, n: int, host: str | None = None, fps: int = 10, width: int = 480):
        self.n, self.host, self.fps, self.width = n, host or DOG_HOST, fps, width
        self.cond = threading.Condition()
        self.frame: bytes | None = None
        self.frame_id = 0
        self.error: str | None = None
        self._viewers = 0
        self._running = False
        self._lock = threading.Lock()

    # --- viewers ---
    def acquire(self) -> None:
        with self._lock:
            self._viewers += 1
            if not self._running:
                self._running = True
                threading.Thread(target=self._run, daemon=True, name=f"cam{self.n}").start()

    def release(self) -> None:
        with self._lock:
            self._viewers -= 1

    def wait_frame(self, last_id: int, timeout: float = 2.0) -> tuple[int, bytes | None]:
        with self.cond:
            self.cond.wait_for(lambda: self.frame_id != last_id, timeout)
            return self.frame_id, self.frame

    # --- worker ---
    def _run(self) -> None:
        from websockets.sync.client import connect
        idle_since: float | None = None
        ff = None
        try:
            while True:
                with self._lock:
                    if self._viewers <= 0:
                        idle_since = idle_since or time.monotonic()
                        if time.monotonic() - idle_since > IDLE_STOP_S:
                            self._running = False
                            return
                    else:
                        idle_since = None
                try:
                    ff = subprocess.Popen(
                        ["ffmpeg", "-loglevel", "error", "-flags", "low_delay",
                         "-probesize", "32", "-analyzeduration", "0", "-f", "h264", "-i", "pipe:0",
                         "-vf", f"fps={self.fps},scale={self.width}:-2,format=yuvj420p", "-q:v", "6",
                         "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                except FileNotFoundError:
                    self.error = "ffmpeg not found (brew install ffmpeg)"
                    self._running = False
                    return
                threading.Thread(target=self._read_jpegs, args=(ff,), daemon=True).start()
                try:
                    with connect(f"ws://{self.host}/cam{self.n}", open_timeout=3, max_size=None) as ws:
                        self.error = None
                        count, last_ack, last_data = 0, 0.0, time.monotonic()
                        while ff.poll() is None:
                            with self._lock:
                                if self._viewers <= 0 and time.monotonic() - (idle_since or time.monotonic()) > IDLE_STOP_S:
                                    break
                                if self._viewers > 0:
                                    idle_since = None
                                elif idle_since is None:
                                    idle_since = time.monotonic()
                            try:
                                data = ws.recv(timeout=0.5)
                                if isinstance(data, bytes):
                                    ff.stdin.write(data)
                                    ff.stdin.flush()
                                    count += 1
                                    last_data = time.monotonic()
                            except TimeoutError:
                                pass
                            if time.monotonic() - last_ack > 0.5:
                                ws.send(struct.pack("<i", count))
                                last_ack = time.monotonic()
                            if time.monotonic() - last_data > 5:
                                raise TimeoutError("no video for 5 s")
                except Exception as e:  # noqa: BLE001 - reconnect loop
                    self.error = f"{type(e).__name__}: {e}"
                    time.sleep(1)
                finally:
                    for stream in (ff.stdin,):
                        try:
                            stream.close()
                        except Exception:  # noqa: BLE001
                            pass
                    ff.kill()
        finally:
            with self._lock:
                self._running = False

    def _read_jpegs(self, ff: subprocess.Popen) -> None:
        buf = b""
        while True:
            chunk = ff.stdout.read1(65536)
            if not chunk:
                return
            buf += chunk
            while True:
                s = buf.find(b"\xff\xd8")
                e = buf.find(b"\xff\xd9", s + 2) if s >= 0 else -1
                if s < 0 or e < 0:
                    break
                jpg, buf = buf[s:e + 2], buf[e + 2:]
                with self.cond:
                    self.frame, self.frame_id = jpg, self.frame_id + 1
                    self.cond.notify_all()


RELAYS: dict[int, CamRelay] = {}


def relay(n: int) -> CamRelay:
    if n not in RELAYS:
        RELAYS[n] = CamRelay(n)
    return RELAYS[n]


def mjpeg(n: int):
    """Generator for a multipart/x-mixed-replace response."""
    r = relay(n)
    r.acquire()
    last = 0
    try:
        while True:
            last, jpg = r.wait_frame(last)
            if jpg is None:
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                   + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n")
    finally:
        r.release()
