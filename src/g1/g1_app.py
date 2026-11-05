"""G1 web app: the Unitree G1 humanoid, simulated in MuJoCo or REAL, with keyboard control, head camera and chat.

Mounted by the chat app at /g1 (simulator only), or standalone:
    python src/g1/g1_app.py --port 8766                       # simulator
    python src/g1/g1_app.py --port 8766 --real --iface en7    # + the real robot (a HUMAN launches this and types `go`)
The physics (and its rendering) start with the first request and idle when nobody is watching.
Real needs: --real at launch, `go` at the terminal, and the browser's explicit arm confirmation. ENTER in the terminal,
the STOP button and Esc/Space are kill switches independent of the model.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from g1_agent import AgentError, G1Agent  # noqa: E402
from g1_real import ARMED, RealError, RealG1, load_cached_actions, load_cached_custom  # noqa: E402
from g1_world import ARM_ACTION_IDS, MAX_VX, MAX_VY, MAX_VYAW, PRESETS, SIM_BY_ID, G1World  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
DEFAULT_CONTROLLER = "lab29"  # the 29-DoF Unitree policy (unitree_rl_lab); "gym12" stays selectable from the UI


class MoveIn(BaseModel):
    vx: float = 0.0
    vy: float = 0.0
    vyaw: float = 0.0


class JogIn(BaseModel):
    rates: dict[str, float]


class PoseIn(BaseModel):
    pose: dict[str, float]


class NameIn(BaseModel):
    name: str


class OrbitIn(BaseModel):
    azimuth: float | None = None
    elevation: float | None = None
    distance: float | None = None


class ModeIn(BaseModel):
    mode: str
    confirm: bool = False


class ProviderIn(BaseModel):
    provider: str


class CtlIn(BaseModel):
    name: str


class FsmIn(BaseModel):
    id: int


class HighIn(BaseModel):
    high: bool


class BalanceIn(BaseModel):
    mode: int


class LoIn(BaseModel):
    value: bool


class ChatIn(BaseModel):
    text: str


class G1Hub:
    """Which body the page drives: the simulator (default) or the real G1 (only if launched with --real)."""

    def __init__(self, sim_factory, real: RealG1 | None = None, log=None):
        self._sim_factory, self._sim, self.real, self.log = sim_factory, None, real, log
        self.mode = "sim"
        # Locomotion-only: the simulator accepts exactly what the real robot accepts (Move/Stop), so what is tried here is what will
        # reach the robot. OFF by default in the simulator (joint jog, Damp... available); the real robot is ALWAYS restricted (see `restricted`).
        self.locomotion_only = False
        self._lock = threading.Lock()

    @property
    def sim(self) -> G1World:
        with self._lock:
            if self._sim is None:  # lazy: the physics thread starts only when someone opens the page
                self._sim = self._sim_factory()
                self._sim.start()
            return self._sim

    @property
    def body(self):
        return self.real if (self.mode == "real" and self.real is not None) else self.sim

    @property
    def restricted(self) -> bool:
        return self.mode == "real" or self.locomotion_only

    def real_armed(self) -> bool:
        return self.real is not None and self.real.state == ARMED

    def set_mode(self, mode: str, confirm: bool = False) -> str | None:
        """Returns a warning when real was entered VIEW-ONLY (camera yes, robot not armed: nothing can move)."""
        warning = None
        if mode == "sim":
            if self.real is not None:
                self.real.disarm()
            self.mode = "sim"
        elif mode == "real":
            if self.real is None:
                raise RealError("The real G1 is not enabled: a person must launch `python src/g1/g1_app.py --real` "
                                "(and type `go` in the terminal). Staying on the simulator.")
            if not confirm:
                raise RealError("Explicit confirmation (checklist) is required to switch to the real G1.")
            try:
                self.real.arm()
            except RealError as e:  # the camera does not need the robot link: keep it, but nothing can be commanded
                warning = f"camera only, robot NOT armed: {e}"
            self.mode = "real"
        else:
            raise RealError(f"unknown mode: {mode!r}")
        if self.log is not None:
            self.log.event("g1_mode", mode=self.mode, warning=warning)
        return warning

    def kill(self, source: str) -> None:
        if self.real is not None and self.mode == "real":
            self.real.kill(source)
        else:
            self.sim.stop()

    def status(self) -> dict:
        return {"mode": self.mode, "real_enabled": self.real is not None, "real_state": self.real.state if self.real else None,
                "locomotion_only": self.restricted, "controller": self._sim.controller if self._sim is not None and self.mode == "sim" else None}


def create_app(world: G1World | None = None, real: RealG1 | None = None, log=None) -> FastAPI:
    app = FastAPI(title="G1")
    hub = G1Hub((lambda: world) if world is not None else (lambda: G1World(controller=DEFAULT_CONTROLLER)), real, log)
    if world is not None:
        world.start()
    agent = G1Agent(hub, log)

    def guard(fn):
        """Run a body command; real-robot refusals come back as {ok: false, error} for the human / the page."""
        try:
            r = fn()
            if isinstance(r, dict):
                return {"ok": True, **r}
            return {"ok": True} if r in (None, True) else {"ok": False, "error": "not available"}
        except RealError as e:
            return {"ok": False, "error": str(e)}

    def refuse_if_restricted():
        """Joint-level arm control is low level (rt/arm_sdk): never on the real robot, and in the simulator it is allowed unless locomotion_only was switched on (API only, no UI)."""
        if hub.restricted:
            return {"ok": False, "error": RealG1.REFUSAL if hub.mode == "real" else
                    "locomotion_only is on: single-joint arm control does not exist on the real robot"}
        return None

    def refuse_if_policy_arms():
        """With the lab29 controller the policy drives the arms: jog and gestures (keyframes on our PD arms) do not apply."""
        if hub.mode == "sim" and hub.sim.controller == "lab29":
            return {"ok": False, "error": "with the lab29 controller the policy drives the arms: switch to gym12 to move them or use gestures"}
        return None

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    def mjpeg(view: str):
        def gen():
            n = -1
            while True:
                b = hub.body
                n, jpeg = b.frame(n, 2.0, view)
                if jpeg is None:
                    time.sleep(0.2)
                    n = -1
                    continue
                yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpeg) + jpeg + b"\r\n"
        return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/stream.mjpg")
    def stream():
        """The 3D view (simulator only; on the real robot this is the head camera too)."""
        return mjpeg("view" if hub.mode == "sim" else "head")

    @app.get("/api/head.mjpg")
    def head():
        """What the robot SEES: the simulator's head camera, or the real one."""
        return mjpeg("head")

    @app.get("/api/state")
    def state():
        if hub.mode == "sim":
            lo, hi = hub.sim.limits()
            limits = {"vx": [float(lo[0]), float(hi[0])], "vy": [float(lo[1]), float(hi[1])], "vyaw": [float(lo[2]), float(hi[2])]}
        else:
            limits = {"vx": MAX_VX, "vy": MAX_VY, "vyaw": MAX_VYAW}
        return {**hub.body.snapshot(), **hub.status(), **agent.status(), "limits": limits}

    @app.get("/api/presets")
    def presets():
        # the robot's own list (live if the real robot is armed and was read, else the copy saved the last time)
        if hub.real is not None and hub.real.actions_source == "robot":
            actions, source, custom = dict(hub.real.actions), "robot", list(hub.real.custom_actions)
        elif load_cached_actions():
            actions, source, custom = load_cached_actions(), "robot (copia salvata)", load_cached_custom()
        else:
            actions, source, custom = dict(ARM_ACTION_IDS), "tabella dell'SDK (il robot non è mai stato letto)", []
        known = set(ARM_ACTION_IDS.values())
        if hub.mode == "sim":
            hub.sim._robot_ids = dict(actions)
        items = [{"name": n, "id": i, "simulated": n in PRESETS or i in SIM_BY_ID, "caution": i not in known, "release": i == 99}
                 for n, i in actions.items()]
        items += [{"name": n, "id": None, "simulated": True, "caution": False, "release": False} for n in PRESETS
                  if n not in actions and n not in ("release_arm",) and ARM_ACTION_IDS.get(n) not in actions.values()]
        return {"source": source, "presets": items, "custom": custom}

    @app.post("/api/move")
    def move(body: MoveIn):
        # On the real robot the arms move only when it is still, and Move does nothing while a gesture runs: the "come il reale"
        # mock does the same. (On the real robot we just pass Move through: the robot ignores it by itself.)
        if hub.mode == "sim" and hub.locomotion_only and hub.body.is_busy():
            return {"ok": False, "error": "gesture running: like on the real robot, walking does not respond until it ends"}
        return guard(lambda: hub.body.command(body.vx, body.vy, body.vyaw))

    @app.post("/api/stop")
    def stop():
        return guard(lambda: hub.body.stop())

    @app.post("/api/kill")
    def kill():
        agent.abort()
        hub.kill("browser")
        return {"ok": True}

    @app.post("/api/jog")
    def jog(body: JogIn):
        return refuse_if_restricted() or refuse_if_policy_arms() or guard(lambda: hub.body.jog(body.rates))

    @app.post("/api/pose")
    def pose(body: PoseIn):
        return refuse_if_restricted() or refuse_if_policy_arms() or guard(lambda: hub.body.set_pose(body.pose))

    @app.post("/api/preset")
    def preset(body: NameIn):
        if hub.mode == "sim" and body.name not in PRESETS and SIM_BY_ID.get(hub.sim._robot_ids.get(body.name)) is None:
            return {"ok": False, "error": f"“{body.name}” is not simulated: it only exists on the real robot"}
        return refuse_if_policy_arms() or guard(lambda: hub.body.play(body.name))

    @app.post("/api/custom")
    def custom(body: NameIn):
        """A move taught in the Unitree app, by exact name (real robot only: the mock cannot show it)."""
        if hub.mode != "real":
            return {"ok": False, "error": "taught actions only exist on the real robot"}
        r = guard(lambda: hub.body.play_custom(body.name))
        return r if r["ok"] else {**r, "error": r.get("error") if r.get("error") != "non disponibile" else "azione sconosciuta al robot"}

    @app.post("/api/custom_stop")
    def custom_stop():
        if hub.mode == "real" and hub.real is not None:
            hub.real.stop_custom()
        return {"ok": True}

    @app.post("/api/damp")
    def damp():
        if hub.restricted:  # like the real robot: no Damp (it makes the robot sag)
            return {"ok": False, "error": "Damp is not available (it makes the robot sag): use STOP or the remote to halt it"}
        return guard(lambda: hub.body.damp())

    @app.post("/api/start")
    def start():
        return guard(lambda: hub.body.reset())

    @app.post("/api/locomotion_only")
    def locomotion_only(body: LoIn):
        """Mock only: switch the simulator between the real robot's set (locomotion) and everything it can do."""
        if hub.mode == "real":
            return {"ok": False, "error": "the real robot is always locomotion-only"}
        agent.abort()
        hub.sim.stop()
        hub.locomotion_only = bool(body.value)
        return {"ok": True, **hub.status()}

    @app.post("/api/fsm")
    def fsm(body: FsmIn):
        """Mode change (SetFsmId, whitelist). Returns what the robot reports afterwards."""
        if hub.restricted and body.id in (1, 702):  # Damp / Lie2StandUp: not on the real robot, so not in the "come il reale" mock
            return {"ok": False, "error": f"FSM {body.id} not available (it can make the robot sag or damage it)"}
        return guard(lambda: hub.body.set_fsm(body.id))

    @app.post("/api/stand_height")
    def stand_height(body: HighIn):
        return guard(lambda: hub.body.stand_height(body.high))

    @app.post("/api/balance_mode")
    def balance_mode(body: BalanceIn):
        return guard(lambda: hub.body.balance_mode(body.mode))

    @app.post("/api/controller")
    def controller(body: CtlIn):
        """Simulator only: which Unitree walking controller drives the G1 (gym12: 12 legs, arms at 90 deg; lab29: all 29 joints)."""
        if hub.mode != "sim":
            return {"ok": False, "error": "the controller can only be chosen in the simulator"}
        agent.abort()
        try:
            ok = hub.sim.set_controller(body.name)
        except Exception as e:  # noqa: BLE001  (e.g. onnxruntime missing)
            return {"ok": False, "error": str(e)}
        return {"ok": bool(ok), **({} if ok else {"error": "unknown controller"}), **hub.status()}

    @app.post("/api/orbit")
    def orbit(body: OrbitIn):
        hub.sim.set_orbit(body.azimuth, body.distance, body.elevation)
        return {"ok": True}

    @app.post("/api/mode")
    def mode(body: ModeIn):
        agent.abort()
        try:
            warning = hub.set_mode(body.mode, body.confirm)
        except RealError as e:
            return {"ok": False, "error": str(e), **hub.status()}
        agent.reset()  # a new body means a new conversation
        return {"ok": True, "warning": warning, **hub.status()}

    # ---- chat
    @app.post("/api/provider")
    def provider(body: ProviderIn):
        """OpenAI <-> Grok for the chat agent. Ends the running mission."""
        try:
            agent.set_provider(body.provider)
        except AgentError as e:
            return {"ok": False, "error": str(e), **agent.status()}
        return {"ok": True, **agent.status()}

    @app.post("/api/chat")
    def chat(body: ChatIn):
        try:
            agent.send(body.text)
        except AgentError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}

    @app.get("/api/events")
    def events(after: int = 0):
        return {"events": agent.events(after), "session": agent.session, **agent.status(), **hub.status()}

    @app.get("/api/frame/{fid}.jpg")
    def frame(fid: int):
        jpeg = agent.frame(fid)
        return Response(jpeg, media_type="image/jpeg") if jpeg else Response(status_code=404)

    @app.post("/api/chat_reset")
    def chat_reset():
        """Empty chat: stops the mission and drops the conversation (events + frames). The robot is not moved."""
        agent.reset()
        return {"ok": True}

    @app.post("/api/abort")
    def abort():
        agent.abort()
        return {"ok": True}

    app.state.hub, app.state.agent = hub, agent
    return app


def main() -> int:
    import uvicorn
    from dotenv import load_dotenv
    from fastapi.staticfiles import StaticFiles

    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--real", action="store_true", help="enable the REAL robot switch (a human launches this)")
    ap.add_argument("--iface", default=None, help="network interface wired to the G1 (or G1_IFACE in .env)")
    args = ap.parse_args()

    sys.path.insert(0, str(root / "src" / "dog"))
    from driver import JsonlLog
    log = JsonlLog(root / "logs" / f"g1-{time.strftime('%Y%m%d')}.jsonl")
    real = None
    if args.real:
        print("REAL G1 ENABLED. Checklist: robot standing in walking mode, >= 2 m clear around it, nobody close, remote in hand.")
        print("ENTER in this terminal = kill switch. Browser: STOP button or Esc/Space.")
        if input("Type 'go' to enable the real-robot switch: ").strip().lower() != "go":
            raise SystemExit("aborted: real G1 not enabled")
        import numpy as np
        probe = G1World.__new__(G1World)  # joint limits only, no physics
        import mujoco
        from g1_world import SCENE, UPPER
        m = mujoco.MjModel.from_xml_path(str(SCENE))
        lim = np.array([m.joint(n + "_joint").range for n in UPPER])
        real = RealG1(args.iface, log=log, limits=(lim[:, 0], lim[:, 1]))
    app = create_app(real=real, log=log)
    app.mount("/ui", StaticFiles(directory=root / "src" / "ui" / "static"), name="ui")
    hub = app.state.hub
    if real is not None and sys.stdin.isatty():
        def keyboard_kill() -> None:  # independent of the model and of the browser
            while True:
                if not sys.stdin.readline():
                    return
                app.state.agent.abort()
                hub.kill("keyboard")
                print("KILL SWITCH (ENTER): G1 stopped. Re-arm from the browser to continue.")
        threading.Thread(target=keyboard_kill, daemon=True, name="kill-switch").start()
    print(f"g1:  http://127.0.0.1:{args.port}  [{'REAL switch enabled' if real else 'simulator only'}]")
    try:
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    finally:
        if real is not None:
            real.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
