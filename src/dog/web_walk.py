"""One-button web page: check the dog is reachable, then walk it forward 0.5 m. Works offline.

    python src/dog/web_walk.py            # mock (default): no dog needed
    python src/dog/web_walk.py --real     # real dog (a human launches this, on the dog's Wi-Fi)

Then open http://127.0.0.1:8770 . The STOP button (and Ctrl+C) halts the dog immediately.
Keep the physical remote in hand anyway.
"""
from __future__ import annotations

import argparse
import asyncio
import threading
import time
from pathlib import Path

import uvicorn
import cams
from driver import Go1Driver, JsonlLog, MockDriver
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

STATIC = Path(__file__).resolve().parent / "static"
UI_STATIC = Path(__file__).resolve().parents[1] / "ui" / "static"
DISTANCE_M = 0.5
SPEED_MS = 0.2  # open loop: the real distance is approximate (ramp-up/down, floor)
TELEOP_VX = 0.2  # m/s while W/S is held (driver hard limit is 0.4)
TELEOP_VYAW = 0.5  # rad/s while A/D is held (driver hard limit is 0.6)
TELEOP_WATCHDOG_S = 0.4  # no message from the browser for this long -> stand still
TELEOP_DT = 0.01

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def create_app(real: bool) -> FastAPI:
    app = FastAPI(title="Go1 walk 50 cm")
    app.mount("/ui", StaticFiles(directory=UI_STATIC), name="ui")  # design system aidea (src/ui/static)
    log = JsonlLog()
    busy = threading.Lock()
    current: dict = {"driver": None}

    @app.get("/")
    def index():
        return FileResponse(STATIC / "walk50.html")

    @app.get("/cam/{n}.mjpg")
    def cam(n: int):
        """Live MJPEG of the dog camera n (1-5). Real dog only: mock has no cameras."""
        if not real or not 1 <= n <= 5:
            return JSONResponse({"error": "cameras only on --real, n in 1..5"}, 404)
        return StreamingResponse(cams.mjpeg(n), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/mode")
    def mode():
        return {"mode": "REAL" if real else "MOCK", "distance_m": DISTANCE_M}

    @app.post("/api/walk")
    def walk():
        if not busy.acquire(blocking=False):
            return JSONResponse({"ok": False, "step": "busy", "error": "A walk is already running."}, 409)
        driver = None
        try:
            driver = Go1Driver(log) if real else MockDriver(log)
            current["driver"] = driver
            try:
                info = driver.connect()  # real: raises ConnectionError if the dog does not answer
            except ConnectionError as e:
                return JSONResponse({"ok": False, "step": "connect", "error": str(e)}, 502)
            res = driver.walk(SPEED_MS, 0.0, DISTANCE_M / SPEED_MS)
            return {"ok": res.ok, "step": "walk", "connect": info, "reason": res.reason,
                    "elapsed_s": res.elapsed_s, "interrupted": res.interrupted}
        except Exception as e:  # noqa: BLE001 - report anything to the page, never hang
            log.event("web_error", error=repr(e))
            return JSONResponse({"ok": False, "step": "error", "error": repr(e)}, 500)
        finally:
            current["driver"] = None
            if driver is not None:
                try:
                    driver.close()
                except Exception:  # noqa: BLE001
                    pass
            busy.release()

    @app.post("/api/stop")
    def stop():
        """Kill switch: lock-free, independent of the walk request."""
        d = current["driver"]
        log.event("kill_switch", source="web", had_driver=d is not None)
        if d is not None:
            d.halt()
        return {"ok": True}

    @app.websocket("/ws/teleop")
    async def teleop(ws: WebSocket):
        """WASD: browser sends {"fwd": -1|0|1, "turn": -1|0|1} on change + every 100 ms (heartbeat).
        Velocities and limits are decided here; silence for TELEOP_WATCHDOG_S means stop."""
        await ws.accept()
        if not busy.acquire(blocking=False):
            await ws.send_json({"type": "error", "error": "Another walk/teleop is running."})
            await ws.close()
            return
        driver = None
        stop_loop = threading.Event()
        state = {"fwd": 0, "turn": 0, "t": time.monotonic()}
        try:
            driver = Go1Driver(log) if real else MockDriver(log)
            current["driver"] = driver
            try:
                info = await asyncio.to_thread(driver.connect)
            except ConnectionError as e:
                await ws.send_json({"type": "error", "error": f"NON connesso: {e}"})
                return
            log.event("teleop_start", driver=driver.name)
            await ws.send_json({"type": "ready", "connect": info})

            def loop() -> None:
                while not stop_loop.is_set() and not driver.halt_event.is_set():
                    fresh = time.monotonic() - state["t"] < TELEOP_WATCHDOG_S
                    fwd, turn = (state["fwd"], state["turn"]) if fresh else (0, 0)
                    driver.drive(fwd * TELEOP_VX, turn * TELEOP_VYAW)
                    time.sleep(TELEOP_DT)

            t = threading.Thread(target=loop, daemon=True)
            t.start()
            while t.is_alive():
                try:
                    msg = await asyncio.wait_for(ws.receive_json(), 0.1)
                except asyncio.TimeoutError:
                    continue
                state["fwd"] = max(-1, min(1, int(msg.get("fwd", 0))))
                state["turn"] = max(-1, min(1, int(msg.get("turn", 0))))
                state["t"] = time.monotonic()
            await ws.send_json({"type": "halted"})
        except WebSocketDisconnect:
            pass
        except Exception as e:  # noqa: BLE001
            log.event("web_error", error=repr(e))
        finally:
            stop_loop.set()
            current["driver"] = None
            if driver is not None:
                log.event("teleop_stop", driver=driver.name)
                try:
                    await asyncio.to_thread(driver.close)  # sends idle for 0.5 s
                except Exception:  # noqa: BLE001
                    pass
            busy.release()

    return app


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--real", action="store_true", help="talk to the real dog (default: mock)")
    p.add_argument("--port", type=int, default=8770)
    args = p.parse_args()
    if args.real:
        print("REAL DOG. Checklist: dog standing, >= 1 m clear in front, remote in hand.")
        if input("Type 'go' to arm: ").strip().lower() != "go":
            raise SystemExit("aborted")
    print(f"open http://127.0.0.1:{args.port}  [{'REAL' if args.real else 'MOCK'}]")
    uvicorn.run(create_app(args.real), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
