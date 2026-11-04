"""Chat with the dog: web UI + OpenAI agent + an always-on MuJoCo window, with a mock/real switch.

    mjpython src/chat/app.py            # macOS (the viewer needs mjpython); simulator only
    python src/chat/app.py              # Linux/Windows
    python src/chat/app.py --headless   # no 3D window (tests)
    mjpython src/chat/app.py --real     # a HUMAN launches this, on the dog's Wi-Fi: enables the REAL switch

Opens the chat on http://127.0.0.1:8765 and the simulator window together. Closing the window
reopens it (the simulator is meant to stay on); Ctrl+C in the terminal stops everything.

The real dog is never reachable unless this was started with `--real` AND the human typed `go` at the terminal.
Even then the browser must confirm ("arm") before anything connects. In real mode every command goes through the
deterministic safety layer in real_body.py; ENTER in this terminal, the STOP button and Esc/Space in the browser
are kill switches independent of the model. Keep the physical remote in hand anyway.
"""
from __future__ import annotations

import argparse
import os
from dataclasses import asdict
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("chat", "dog", "sim"):
    sys.path.insert(0, str(ROOT / "src" / sub))

import cameras  # noqa: E402
import uvicorn  # noqa: E402
from driver import Go1Driver, JsonlLog  # noqa: E402
from dog_agent import AgentError, DogAgent  # noqa: E402
import commands  # noqa: E402
from dog_world import DogSim  # noqa: E402
from sim_body import SimBody  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse  # noqa: E402
from hub import HubError, RobotHub  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from real_body import RealBody  # noqa: E402
import settings as agent_settings  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
UI_STATIC = Path(__file__).resolve().parents[1] / "ui" / "static"
REAL_CAMS = tuple(c.n for c in cameras.CAMERAS)  # front, down, side (cam3 is black, cam5 unavailable; 4/11)


class ChatIn(BaseModel):
    message: str


class SpeedIn(BaseModel):
    time_scale: float


class BrainIn(BaseModel):
    brain: str


class ModeIn(BaseModel):
    mode: str
    confirm: bool = False


def create_app(hub: RobotHub, sim: DogSim, agent: DogAgent) -> FastAPI:
    app = FastAPI(title="Chat col cane")
    app.mount("/ui", StaticFiles(directory=UI_STATIC), name="ui")  # design system aidea (src/ui/static)

    def _log_call(request: Request) -> None:  # who pressed Stop / Reset demo (browser vs. script)
        agent._log("api_call", path=request.url.path, client=request.client.host if request.client else None,
                   user_agent=request.headers.get("user-agent", "")[:80])

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.post("/api/chat")
    def chat(body: ChatIn):
        text = body.message.strip()
        if not text:
            return {"error": "Messaggio vuoto."}
        try:
            agent.send(text)  # starts a mission (or feeds the running one); progress arrives via /api/events
        except AgentError as e:
            return {"error": str(e)}
        return {"ok": True}

    @app.get("/api/events")
    def events(after: int = 0):
        hub.heartbeat()  # the browser is alive: the real-dog watchdog is fed by this poll
        return {"events": agent.events(after), **agent.status(), **hub.status()}

    @app.get("/api/frame/{frame_id}.jpg")
    def frame(frame_id: int):
        jpeg = agent.frame(frame_id)
        if jpeg is None:
            return Response(status_code=404)
        return Response(jpeg, media_type="image/jpeg", headers={"Cache-Control": "max-age=3600"})

    @app.get("/api/state")
    def state():
        hub.heartbeat()
        return {**hub.body.snapshot(), **agent.status(), **hub.status()}

    @app.post("/api/mode")
    def set_mode(body: ModeIn, request: Request):
        """Mock <-> real switch. Always aborts the running mission first. Real needs --real at launch + confirm."""
        _log_call(request)
        agent.abort()
        try:
            status = hub.set_mode(body.mode, body.confirm)
        except HubError as e:
            return {"ok": False, "error": str(e), **hub.status()}
        agent.reset()  # a new body means a new conversation (history from the other body would mislead the model)
        return {"ok": True, **status}

    @app.post("/api/brain")
    def set_brain(body: BrainIn, request: Request):
        """LLM agent <-> JEV (Decisions API) switch. Ends the running mission; the conversation is kept."""
        _log_call(request)
        try:
            agent.set_brain(body.brain)
        except AgentError as e:
            return {"ok": False, "error": str(e), "brain": agent.brain}
        return {"ok": True, "brain": agent.brain}

    @app.get("/api/settings")
    def get_settings():
        return {"settings": asdict(agent.settings.get()), "defaults": asdict(agent_settings.DEFAULTS),
                "choices": {"resolutions": agent_settings.RESOLUTIONS, "efforts": agent_settings.EFFORTS,
                            "cams": [{"name": c.name, "label": c.label} for c in cameras.CAMERAS]}}

    @app.post("/api/settings")
    def set_settings(body: dict, request: Request):
        """Live settings of the agent loop (cameras, resolution, JEV options...). Applied at the next step."""
        _log_call(request)
        cfg = agent.settings.update(body)
        agent._log("settings_changed", settings=asdict(cfg))
        return {"ok": True, "settings": asdict(cfg)}

    @app.post("/api/settings/reset")
    def reset_settings(request: Request):
        _log_call(request)
        return {"ok": True, "settings": asdict(agent.settings.reset())}

    @app.get("/cam/{n}.mjpg")
    def real_cam(n: int):
        """Live MJPEG of dog camera n (read-only relay in src/dog/cams.py). Only if launched with --real."""
        if not hub.real_enabled or n not in REAL_CAMS:
            return JSONResponse({"error": f"real cameras need --real; n in {list(REAL_CAMS)}"}, 404)
        import cams
        return StreamingResponse(cams.mjpeg(n), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/cams")
    def cam_status():
        if not hub.real_enabled:
            return {"cams": []}
        import cams
        return {"cams": [{"n": n, "error": cams.relay(n).error} for n in REAL_CAMS]}

    @app.get("/api/cameras")
    def camera_list():
        """The same 3 cameras in mock and real mode: name, real Go1 number, label, placement told to the model."""
        return {"cameras": [{"name": c.name, "n": c.n, "label": c.label, "where": c.where} for c in cameras.CAMERAS]}

    @app.get("/api/camera.jpg")
    def camera(cam: str = "front"):
        """Simulator frame of camera `cam` (front/down/side). In real mode the browser uses /cam/<n>.mjpg."""
        if cam not in cameras.BY_NAME:
            return JSONResponse({"error": f"cam in {list(cameras.BY_NAME)}"}, 404)
        jpeg = sim.capture(480, 360, camera=cam)
        if jpeg is None:
            return Response(status_code=503)
        return Response(jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.post("/api/stop")
    def stop(request: Request):
        _log_call(request)
        hub.kill("web")  # first the body (real dog: lock-free halt, latches HALTED), then the mission
        agent.abort()
        return {"ok": True, **hub.status()}

    @app.post("/api/speed")
    def speed(body: SpeedIn):
        sim.set_time_scale(body.time_scale)
        return {"time_scale": sim.time_scale}

    @app.post("/api/reset-demo")
    def reset_demo(request: Request):
        _log_call(request)
        agent.reset()  # ends the mission, forgets the conversation
        hub.body.reset_pose()  # simulator: dog (and props) back to the start; real dog: only zeroes the odometry
        return {"ok": True}

    @app.get("/api/commands")
    def commands():
        return {name: spec["description"] for name, spec in commands.tool_specs().items()}

    return app


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--headless", action="store_true", help="no 3D window")
    ap.add_argument("--real", action="store_true",
                    help="enable the REAL dog switch (a human launches this, on the dog's Wi-Fi)")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    log = JsonlLog(ROOT / "logs" / f"chat-{time.strftime('%Y%m%d')}.jsonl")
    world = DogSim(headless=args.headless, log=log)  # the MuJoCo physics, viewer and cameras
    sim = SimBody(world, log)  # the simulated dog as a body: same commands as the real one

    real = None
    if args.real:
        print("REAL DOG ENABLED. Checklist: dog standing, >= 1.5 m clear around it, nobody close, remote in hand.")
        print("ENTER in this terminal = kill switch. Browser: STOP button or Esc/Space.")
        if input("Type 'go' to enable the real-dog switch: ").strip().lower() != "go":
            raise SystemExit("aborted: real dog not enabled")
        import cams  # read-only camera relay (needs ffmpeg), started only while someone looks
        real = RealBody(lambda lg: Go1Driver(lg), log, camera=cams.relay(1),
                        extra_cameras={c.name: cams.relay(c.n) for c in cameras.CAMERAS if c.name != "front"})
    hub = RobotHub(sim, real, log)
    agent = DogAgent(hub, log)

    if real is not None and sys.stdin.isatty():
        def keyboard_kill() -> None:  # independent of the model and of the browser
            while True:
                if not sys.stdin.readline():
                    return
                hub.kill("keyboard")
                agent.abort()
                print("KILL SWITCH (ENTER): dog halted. Re-arm from the browser to continue.")
        threading.Thread(target=keyboard_kill, daemon=True, name="kill-switch").start()

    server = uvicorn.Server(uvicorn.Config(create_app(hub, sim, agent), host="127.0.0.1", port=args.port,
                                           log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    print(f"chat:  http://127.0.0.1:{args.port}  [{'REAL switch enabled' if real else 'simulator only'}]\n"
          f"log:   {log.path}\nCtrl+C per fermare tutto")
    try:
        world.run()  # main thread: owns the viewer
    except KeyboardInterrupt:
        pass
    finally:
        if real is not None:
            real.shutdown()  # halts and disarms
        sim.shutdown()
        world.shutdown()
        server.should_exit = True
    return 0


if __name__ == "__main__":
    sys.exit(main())
