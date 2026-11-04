"""G1 web app: the Unitree G1 humanoid in MuJoCo, driven with WASD (high-level velocity commands only).

Mounted by the chat app at /g1 (src/chat/app.py), or standalone:  python src/g1/g1_app.py --port 8766
The physics (and its rendering) start with the first request and idle when nobody is watching.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from g1_world import MAX_VX, MAX_VY, MAX_VYAW, G1World  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"


class MoveIn(BaseModel):
    vx: float = 0.0
    vy: float = 0.0
    vyaw: float = 0.0


class OrbitIn(BaseModel):
    azimuth: float | None = None
    elevation: float | None = None
    distance: float | None = None


def create_app(world: G1World | None = None) -> FastAPI:
    app = FastAPI(title="G1")
    holder: dict[str, G1World] = {}

    def get_world() -> G1World:
        if world is not None:
            return world
        if "w" not in holder:  # lazy: the physics thread starts only when someone opens /g1
            holder["w"] = G1World()
            holder["w"].start()
        return holder["w"]

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/stream.mjpg")
    def stream():
        w = get_world()

        def gen():
            n = -1
            while True:
                n, jpeg = w.frame(n)
                if jpeg is None:
                    continue
                yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpeg) + jpeg + b"\r\n"

        return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/state")
    def state():
        return {**get_world().snapshot(), "limits": {"vx": MAX_VX, "vy": MAX_VY, "vyaw": MAX_VYAW}}

    @app.post("/api/move")
    def move(body: MoveIn):
        """Velocity command (m/s, m/s, rad/s). The browser repeats it while a key is held; silence for 0.4 s = stop."""
        get_world().command(body.vx, body.vy, body.vyaw)
        return {"ok": True}

    @app.post("/api/stop")
    def stop():
        get_world().stop()
        return {"ok": True}

    @app.post("/api/reset")
    def reset():
        get_world().reset()
        return {"ok": True}

    @app.post("/api/orbit")
    def orbit(body: OrbitIn):
        get_world().set_orbit(body.azimuth, body.distance, body.elevation)
        return {"ok": True}

    return app


def main() -> int:
    import uvicorn
    from fastapi.staticfiles import StaticFiles

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8766)
    args = ap.parse_args()
    app = create_app()
    app.mount("/ui", StaticFiles(directory=Path(__file__).resolve().parents[1] / "ui" / "static"), name="ui")
    print(f"g1:  http://127.0.0.1:{args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
