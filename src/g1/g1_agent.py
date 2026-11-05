"""G1Agent: chat with the G1. An LLM sees the HEAD CAMERA (sim: MuJoCo head_cam, real: the robot's camera), and acts
through a small whitelist of tools. Same provider switch as the dog's agent (src/llm_provider.py: OpenAI or Grok).

Safety (src/g1/README.md): the model never gets raw velocities, Damp/Start, joint control or anything but the tools below.
Every move is bounded in speed and duration, executed one at a time, and abort()/kill stop it from outside the model.
"""
from __future__ import annotations

import base64
import json
import os
import secrets
import sys
import threading
import time
from pathlib import Path

from g1_world import ARM_ACTION_IDS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/llm_provider.py
import llm_provider  # noqa: E402
GESTURES = [n for n in ARM_ACTION_IDS if n != "release_arm"] + ["wave_hand"]
# Cruise commands (vx, vy, vyaw) in m/s and rad/s. The real robot does NOT step below ~0.2 m/s and needs about a second to start walking
# (issue #170 of unitree_sdk2_python + our own test: 0.2 m/s for 2 s gave half a step), so the model never picks a speed: it asks for a
# DISTANCE or an ANGLE and the code walks at a speed above that floor. Clipped to the body's own limits.
CRUISE = {"walk_forward": (0.4, 0, 0), "walk_backward": (-0.3, 0, 0), "strafe_left": (0, 0.25, 0), "strafe_right": (0, -0.25, 0),
          "turn_left": (0, 0, 0.6), "turn_right": (0, 0, -0.6)}
AMOUNT = {"walk_forward": (0.2, 3.0), "walk_backward": (0.2, 2.0), "strafe_left": (0.2, 1.5), "strafe_right": (0.2, 1.5),
          "turn_left": (10.0, 180.0), "turn_right": (10.0, 180.0)}  # metres, or degrees for turn_*
STARTUP_S = {"walk": 0.8, "turn": 0.5}  # open loop (real robot, no odometry yet): time the controller needs to get stepping. CALIBRATE on the robot
MAX_PLAN_STEPS = 4
SEARCH_RIGHT_DEG, SEARCH_LEFT_DEG = 30, 60  # lost target: small turn right, then left (60 = back to the start + 30 on the other side), then stand still
MAX_CONSECUTIVE_MOVES = 3  # WALKING moves in a row, then the model must look or finish (pure turns do not count)

TOOLS = [
    {"type": "function", "name": "move", "description":
        "Ti muovi di una DISTANZA (metri) o ruoti di un ANGOLO (gradi), in una lista di 1-4 passi eseguiti uno dopo l'altro senza pause. "
        "walk_forward/walk_backward/strafe_left/strafe_right: amount in METRI (0,2-3). turn_left/turn_right: amount in GRADI (10-180). "
        "Concatena i passi che ti servono in una sola chiamata (es. gira 90° e poi avanti 1 m) invece di fare tanti micro-movimenti: "
        "tra una chiamata e l'altra passano diversi secondi. Alla fine ti fermi e ricevi una nuova immagine.",
     "parameters": {"type": "object", "properties": {
         "steps": {"type": "array", "minItems": 1, "maxItems": MAX_PLAN_STEPS, "items": {"type": "object", "properties": {
             "action": {"type": "string", "enum": list(CRUISE)},
             "amount": {"type": "number", "description": "metri (walk/strafe) o gradi (turn)"}},
             "required": ["action", "amount"], "additionalProperties": False}},
         "thought": {"type": "string", "description": "perché, in una frase"}},
         "required": ["steps", "thought"], "additionalProperties": False}},
    {"type": "function", "name": "gesture", "description":
        "Un gesto con le braccia (resti fermo sul posto). Usalo per salutare, dare il cinque, stringere la mano, ecc.",
     "parameters": {"type": "object", "properties": {
         "name": {"type": "string", "enum": GESTURES}, "thought": {"type": "string"}},
         "required": ["name", "thought"], "additionalProperties": False}},
    {"type": "function", "name": "look", "description":
        "Resta fermo e guarda di nuovo (nuova immagine della telecamera). Se stai cercando un oggetto e NON lo vedi, chiamalo con "
        "target_visible=false: la ricerca (una piccola rotazione a destra, poi a sinistra) la fa il sistema; se non lo trova resta fermo e "
        "chiede indicazioni all'utente. Non ruotare tu per cercare.",
     "parameters": {"type": "object", "properties": {
         "target_visible": {"type": "boolean", "description": "false se cerchi un oggetto e non lo vedi; true se lo vedi; ometti se non cerchi nulla"},
         "thought": {"type": "string"}}, "required": ["thought"], "additionalProperties": False}},
    {"type": "function", "name": "finish", "description": "Obiettivo raggiunto (o impossibile): rispondi all'utente.",
     "parameters": {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"],
                    "additionalProperties": False}},
]


def describe_call(name: str, args: dict) -> str:
    """Compact, readable form of a tool call for the model's history (and the UI): 'move(walk forward 1 m -> turn left 30°)'."""
    if name == "move" and isinstance(args.get("steps"), list):
        parts = []
        for st in args["steps"]:
            if isinstance(st, dict):
                act = str(st.get("action", "?"))
                parts.append(f"{act.replace('_', ' ')} {st.get('amount', '?')}{'°' if act.startswith('turn') else ' m'}")
        return "move(" + " -> ".join(parts) + ")"
    return f"{name}({', '.join(f'{k}={v}' for k, v in args.items() if k != 'thought')})"


def system_prompt(real: bool) -> str:
    return (
        "Sei un robot umanoide Unitree G1 (" + ("VERO, in una stanza con delle persone: non urtare nessuno" if real else "simulato in MuJoCo") + ").\n\n"
        "COSA VEDI. Solo ciò che mostra la telecamera sulla tua testa, che guarda dritto davanti a te: l'asse del robot passa per il CENTRO "
        "dell'immagine. È un grandangolo" + (" (circa 70° in orizzontale: il bordo destro/sinistro è a ~35° dall'asse)" if not real else
        " (non conosco l'angolo esatto: stima gli angoli a occhio e correggi guardando di nuovo)") + ", quindi le cose sembrano più "
        "vicine di quanto siano. Non vedi te stesso né ciò che sta dietro o ai lati.\n\n"
        "COME TI MUOVI. Un solo tool, move, con una lista di 1-4 passi eseguiti in sequenza senza pause. Ogni passo ha un'azione e una quantità:\n"
        "- walk_forward / walk_backward: avanti / indietro, quantità in METRI (0,2-3 avanti, 0,2-2 indietro).\n"
        "- strafe_left / strafe_right: passo laterale a sinistra / destra senza ruotare, in METRI (0,2-1,5).\n"
        "- turn_left / turn_right: ruoti sul posto a sinistra (antiorario) / destra (orario), in GRADI (10-180).\n"
        "Destra e sinistra sono quelle del ROBOT, non dell'immagine vista da fuori: ciò che sta nella metà destra dell'immagine è alla tua destra. "
        "La velocità non la scegli tu: la camminata è già calibrata, quindi distanza e angolo che indichi sono quelli che farai.\n\n"
        "COME RAGGIUNGERE UN OGGETTO. 1) Se NON lo vedi nell'immagine, chiama look con target_visible=false: la ricerca (una piccola rotazione a "
        "destra, poi una a sinistra) la faccio io; se non lo trovo resto fermo e chiedo indicazioni all'utente. Non ruotare tu per cercare e non "
        "vagare. 2) Se lo vedi decentrato, ruota ESATTAMENTE dell'angolo che stimi" + (" con (posizione orizzontale − 0,5) × 70°, dove la posizione va da "
        "0 (bordo sinistro) a 1 (bordo destro): ad esempio un oggetto a 0,85 è a ~25° a destra" if not real else
        " guardando quanto è lontano dal centro (più è lontano, più devi ruotare)") + "; non ruotare a caso di 30° e non ruotare due volte di "
        "fila per centrarlo senza guardare. 3) Avanza con walk_forward di circa i due terzi della distanza che stimi, poi controlla con look e "
        "rifinisci. 4) «Mettiti davanti a X» = fermarti a circa mezzo metro da X, rivolto verso di lui: non urtarlo e non andare oltre. "
        "Puoi concatenare più passi nella stessa chiamata (es. turn_right 20°, poi walk_forward 2 m). Dopo ogni movimento leggi il risultato: "
        "ti dice quanto ti sei mosso e ruotato davvero, e se c'è stato uno scostamento rispetto a ciò che avevi chiesto.\n\n"
        "REGOLE. Se l'utente chiede una distanza o un angolo precisi (es. «un metro avanti», «gira di 90°»), fai UNA sola chiamata move con quel "
        "valore: viene eseguito esattamente come chiesto, quindi poi basta un eventuale look e finish. Non fare micro-movimenti (almeno 0,3 m, "
        "almeno 20° per una rotazione): ogni chiamata costa diversi secondi. Non aggiustare a meno che l'immagine mostri un ostacolo o un errore "
        "evidente. Prima di avanzare controlla che lo spazio sia libero. Altri tool: gesture (un gesto con le braccia, fermo sul posto), look "
        "(guarda di nuovo), finish (concludi e rispondi all'utente). Se l'obiettivo è una domanda, guarda e rispondi con finish. "
        "Parla all'utente in italiano, breve.")


class AgentError(Exception):
    pass


class G1Agent:
    MAX_STEPS = int(os.environ.get("G1_MAX_STEPS") or 20)

    def __init__(self, hub, log=None):
        self.hub, self.log = hub, log
        self._events: list[dict] = []
        self._frames: dict[int, bytes] = {}
        # Ids only ever grow (also across reset()): the page remembers the last id it saw, so ids that restart from 1 would hide every new
        # message. `session` changes when the process restarts, so a page that stayed open across a restart starts from scratch.
        self.session = secrets.token_hex(4)
        self._next_event = 1
        self._next_frame = 1
        self._lock = threading.Lock()
        self._epoch = 0
        self._thread: threading.Thread | None = None
        self.running = False
        self.phase = "idle"
        self.provider = llm_provider.default_provider()  # "openai" | "grok" (src/llm_provider.py)

    # ---- public
    def set_provider(self, provider: str) -> None:
        if provider not in llm_provider.PROVIDERS:
            raise AgentError(f"unknown provider: {provider!r}")
        self.abort()  # a running mission keeps its model: switching ends it
        self.provider = provider

    def send(self, text: str) -> None:
        if self.running:
            raise AgentError("a mission is already running: stop it (Stop) or wait")
        lc = llm_provider.config(self.provider)
        if not llm_provider.key_ok(lc):
            raise AgentError(llm_provider.missing_key_message(lc))
        mode = self.hub.mode
        if mode == "real" and not self.hub.real_armed():
            raise AgentError("The real G1 is not armed: arm it from the Real button")
        self._epoch += 1
        epoch = self._epoch
        self._emit("user", text=text)
        self.running, self.phase = True, "start"
        self._thread = threading.Thread(target=self._run, args=(text, epoch, mode), daemon=True, name="g1-agent")
        self._thread.start()

    def abort(self) -> None:
        self._epoch += 1
        try:
            self.hub.body.stop()
        except Exception:  # noqa: BLE001
            pass
        self.running, self.phase = False, "idle"

    def reset(self) -> None:
        self.abort()
        with self._lock:
            self._events, self._frames = [], {}

    def events(self, after: int = 0) -> list[dict]:
        with self._lock:
            return [e for e in self._events if e["id"] > after]

    def frame(self, fid: int) -> bytes | None:
        return self._frames.get(fid)

    def status(self) -> dict:
        return {"running": self.running, "phase": self.phase, "provider": self.provider, "model": llm_provider.config(self.provider).model}

    # ---- internals
    def _emit(self, kind: str, **f) -> None:
        with self._lock:
            e = {"id": self._next_event, "kind": kind, **f}
            self._next_event += 1
            self._events.append(e)
        if self.log is not None:
            self.log.event("g1_agent_" + kind, **{k: v for k, v in f.items() if k != "frame"})

    def _store(self, jpeg: bytes) -> int:
        with self._lock:
            fid = self._next_frame
            self._next_frame += 1
            self._frames[fid] = jpeg
            for old in [k for k in self._frames if k < fid - 60]:
                del self._frames[old]
        return fid

    def _run(self, goal: str, epoch: int, mode: str) -> None:
        try:
            self._mission(goal, epoch, mode)
        except AgentError as e:
            self._emit("error", text=str(e))
        except Exception as e:  # noqa: BLE001
            self._emit("error", text=f"{type(e).__name__}: {e}")
        finally:
            if self._epoch == epoch:
                self.running, self.phase = False, "idle"
                try:
                    self.hub.body.stop()
                except Exception:  # noqa: BLE001
                    pass

    def _wait_idle(self, epoch: int, seconds: float) -> None:
        t = time.monotonic()
        while time.monotonic() - t < seconds and self._epoch == epoch:
            time.sleep(0.05)
        while self.hub.body.is_busy() and self._epoch == epoch and time.monotonic() - t < 15:
            time.sleep(0.1)

    def _mission(self, goal: str, epoch: int, mode: str) -> None:
        from openai import OpenAIError
        lc = llm_provider.config(self.provider)  # fixed for the whole mission: switching provider aborts it
        client = llm_provider.make_client(lc)
        model, effort = lc.model, lc.effort
        max_steps = min(self.MAX_STEPS, 12) if mode == "real" else self.MAX_STEPS
        done: list[str] = []
        moved = {"fwd": 0.0, "lat": 0.0, "yaw": 0.0}  # what the model has already been commanded to do this mission
        consec = 0
        misses = 0  # consecutive look(target_visible=false)
        for step in range(1, max_steps + 1):
            if self._epoch != epoch:
                return
            self.phase = "vedo"
            jpeg = self.hub.body.head_jpeg()
            if jpeg is None:
                raise AgentError("no image from the head camera" +
                                 (": check G1_CAMERA_URL" if mode == "real" else ""))
            fid = self._store(jpeg)
            text = (f"Obiettivo: {goal}\nPassi fatti finora ({len(done)}): " + ("; ".join(done[-12:]) or "nessuno") +
                    f"\nSpostamento totale già eseguito (come comandato): avanti {moved['fwd']:+.2f} m, a sinistra {moved['lat']:+.2f} m, "
                    f"rotazione a sinistra {moved['yaw']:+.0f}°. Se l'obiettivo era una distanza o un angolo precisi e sono già stati eseguiti, "
                    f"concludi con finish." +
                    f"\nPasso {step}/{max_steps}. Questa è la tua telecamera adesso:")
            tools = self._tools()
            kwargs: dict = {"model": model, "instructions": system_prompt(mode == "real"), "tools": tools,
                            "tool_choice": "required", "parallel_tool_calls": False,
                            "input": [{"role": "user", "content": [
                                {"type": "input_text", "text": text},
                                {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}]}]}
            if effort:
                kwargs["reasoning"] = {"effort": effort}
            self.phase = "penso"
            t0 = time.monotonic()
            try:
                resp = client.responses.create(**kwargs)
            except OpenAIError as e:
                raise AgentError(f"{lc.label} API error: {e}") from e
            if self._epoch != epoch:
                return
            calls = [o for o in resp.output if o.type == "function_call"]
            if not calls:
                self._emit("final", text=resp.output_text or "(nessuna risposta)")
                return
            name = calls[0].name
            try:
                args = json.loads(calls[0].arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            thought = str(args.get("thought", "")).strip()
            if name == "finish":
                self._emit("final", text=str(args.get("message", "")), frame=fid)
                return
            walks = False
            if name == "move":
                parsed = self._validate_steps(args)[0] or []
                walks = any(not a.startswith("turn") for a, _ in parsed)
            if name == "look" and args.get("target_visible") is False:
                misses += 1  # the model does not see the target: we search for it, it does not wander
                if misses >= 3:
                    self._emit("step", n=step, frame=fid, tool=name, args={"target_visible": False}, thought=thought, ok=True,
                               result="ricerca finita: davanti, a destra e a sinistra", latency=round(time.monotonic() - t0, 2))
                    self._emit("final", frame=fid, text="Non trovo l'obiettivo: ho guardato davanti, un po' a destra e un po' a sinistra. "
                                                        "Resto fermo e aspetto indicazioni.")
                    return
                action, amount = ("turn_right", SEARCH_RIGHT_DEG) if misses == 1 else ("turn_left", SEARCH_LEFT_DEG)
                ok, result = self._move({"steps": [{"action": action, "amount": amount}]}, epoch)
                result = (f"Ricerca {misses}/2: non vedevi l'obiettivo, ho ruotato {action.replace('_', ' ')} {amount}°. {result} "
                          "Se ora lo vedi procedi; se non lo vedi richiama look con target_visible=false.")
            elif name == "move" and walks and consec >= MAX_CONSECUTIVE_MOVES:
                ok, result = False, (f"hai già fatto {consec} movimenti di fila: guarda (look) per controllare, oppure concludi con finish. "
                                     "Spostamento totale già eseguito: avanti %+.2f m, a sinistra %+.2f m, rotazione %+.0f°." %
                                     (moved["fwd"], moved["lat"], moved["yaw"]))
            else:
                ok, result = self._execute(name, args, epoch)
                if name != "look" or args.get("target_visible") is not False:
                    misses = 0 if name in ("move", "gesture") or args.get("target_visible") is True else misses
            if name == "move":
                consec = consec + 1 if (ok and walks) else consec
            else:
                consec = 0
            if name == "move" and ok:
                for action, amount in (self._validate_steps(args)[0] or []):
                    sign = 1 if action in ("walk_forward", "strafe_left", "turn_left") else -1
                    key = "yaw" if action.startswith("turn") else ("fwd" if action.startswith("walk") else "lat")
                    moved[key] += sign * amount
            self._emit("step", n=step, frame=fid, tool=name, args={k: v for k, v in args.items() if k != "thought"},
                       thought=thought, ok=ok, result=result, latency=round(time.monotonic() - t0, 2))
            done.append(describe_call(name, args) + ("" if ok else f" RIFIUTATO: {result}"))
        self._emit("final", text="Ho raggiunto il limite di passi: mi fermo qui.")

    def _execute(self, name: str, args: dict, epoch: int) -> tuple[bool, str]:
        """Validator + executor: everything the model asks is checked here, against the whitelist and the limits."""
        body = self.hub.body
        try:
            if name == "move":
                return self._move(args, epoch)
            if name == "gesture":
                g = args.get("name")
                if g not in self._gestures():
                    return False, "gesto non ammesso"
                self.phase = "gesto"
                if not body.play(g):
                    return False, "gesto non disponibile"
                time.sleep(0.5)
                self._wait_idle(epoch, 0.0)
                return True, "fatto"
            if name == "look":
                time.sleep(0.5)
                return True, "ok"
            return False, f"tool sconosciuto: {name}"
        except Exception as e:  # noqa: BLE001  (RealError etc.: reported to the model, never raised)
            return False, str(e)

    def _gestures(self) -> list[str]:
        """The gestures the CURRENT body can do: the real robot's own list, or what the simulator can show."""
        body = self.hub.body
        if hasattr(body, "agent_gestures"):
            return list(body.agent_gestures())
        return list(body.gesture_names()) if hasattr(body, "gesture_names") else list(GESTURES)

    def _tools(self) -> list[dict]:
        import copy
        tools = copy.deepcopy(TOOLS)
        for t in tools:
            if t["name"] == "gesture":
                t["parameters"]["properties"]["name"]["enum"] = self._gestures()
        return tools

    # ---- bounded moves: distance/angle in, validated, closed loop on the simulator, timed on the real robot
    @staticmethod
    def _limits(body) -> tuple[list[float], list[float]]:
        """(low, high) of (vx, vy, vyaw) of the body, so the planned time uses the speed the body will really accept."""
        if hasattr(body, "limits"):
            lo, hi = body.limits()
            return [float(x) for x in lo], [float(x) for x in hi]
        import g1_real
        hi = [g1_real.REAL_MAX_VX, g1_real.REAL_MAX_VY, g1_real.REAL_MAX_VYAW]
        return [-x for x in hi], hi

    def _validate_steps(self, args: dict) -> tuple[list[tuple[str, float]] | None, str]:
        steps = args.get("steps")
        if not isinstance(steps, list) or not (1 <= len(steps) <= MAX_PLAN_STEPS):
            return None, f"steps: serve una lista di 1-{MAX_PLAN_STEPS} passi"
        out: list[tuple[str, float]] = []
        for i, st in enumerate(steps, 1):
            if not isinstance(st, dict) or st.get("action") not in CRUISE:
                return None, f"passo {i}: action non ammessa (ammesse: {', '.join(CRUISE)})"
            try:
                amount = float(st.get("amount"))
            except (TypeError, ValueError):
                return None, f"passo {i}: amount non numerico"
            lo, hi = AMOUNT[st["action"]]
            if not (lo <= amount <= hi):
                unit = "gradi" if st["action"].startswith("turn") else "metri"
                return None, f"passo {i}: amount {amount:g} fuori dai limiti ({lo:g}-{hi:g} {unit})"
            out.append((st["action"], amount))
        return out, ""

    def _move(self, args: dict, epoch: int) -> tuple[bool, str]:
        """Run the validated steps. Simulator: closed loop (stops at the asked distance/angle, HOLDS the heading while walking, slows down before
        the end of a turn, and reports asked vs measured). Real robot: timed, no odometry yet."""
        import math
        steps, err = self._validate_steps(args)
        if steps is None:
            return False, err
        body = self.hub.body
        closed = getattr(body, "name", "sim") != "real"  # the simulator reports its pose; the real robot: timed (no odometry wired yet)
        lo, hi = self._limits(body)

        def wrap(a: float) -> float:
            return (a + math.pi) % (2 * math.pi) - math.pi

        self.phase = "cammino"
        start = body.snapshot() if closed else None
        report: list[str] = []
        deviated = False
        for action, amount in steps:
            cmd = [min(max(c, l), h) for c, l, h in zip(CRUISE[action], lo, hi)]
            axis = max(range(3), key=lambda k: abs(CRUISE[action][k]))
            speed = abs(cmd[axis])
            if speed < 0.15:
                return False, f"{action}: il robot non accetta una velocità sufficiente ({speed:.2f})"
            turn = action.startswith("turn")
            target = math.radians(amount) if turn else amount  # rad or m
            budget = target / speed * 2.0 + 3.0 if closed else target / speed + STARTUP_S["turn" if turn else "walk"]
            s0 = body.snapshot() if closed else None
            h0 = math.radians(s0["yaw_deg"]) if closed else 0.0
            prog, t0 = 0.0, time.monotonic()
            while time.monotonic() - t0 < budget:
                if self._epoch != epoch:
                    body.stop()
                    return False, "interrotto"
                now = list(cmd)
                if closed:
                    yaw = math.radians(body.snapshot()["yaw_deg"])
                    if turn:  # slow down over the last ~0.4 rad so it does not overshoot the asked angle
                        now[2] = math.copysign(max(0.15, min(abs(cmd[2]), 1.5 * (target - prog))), cmd[2])
                    else:  # hold the heading: the gait drifts in yaw, and a few degrees of drift over 2 m lose the target
                        now[2] = max(-0.35, min(0.35, 1.5 * wrap(h0 - yaw)))
                body.command(*now)
                time.sleep(0.1)
                if closed:
                    s = body.snapshot()
                    dx, dy = s["x"] - s0["x"], s["y"] - s0["y"]
                    fwd, lat = dx * math.cos(h0) + dy * math.sin(h0), -dx * math.sin(h0) + dy * math.cos(h0)
                    dyaw = wrap(math.radians(s["yaw_deg"]) - h0)
                    prog = {"walk_forward": fwd, "walk_backward": -fwd, "strafe_left": lat, "strafe_right": -lat,
                            "turn_left": dyaw, "turn_right": -dyaw}[action]
                    if prog >= target - (0.03 if turn else 0.03):
                        break
            if closed:
                e = body.snapshot()
                if turn:
                    got = math.degrees(prog)
                    deviated |= abs(got - amount) > max(8.0, 0.25 * amount)
                    report.append(f"{action} {amount:g}° (misurato {got:.0f}°)")
                else:
                    drift = math.degrees(wrap(math.radians(e["yaw_deg"]) - h0))
                    deviated |= abs(prog - amount) > 0.3 or abs(drift) > 12
                    report.append(f"{action} {amount:g} m (misurato {prog:.2f} m, rotta deviata di {drift:+.0f}°)")
            else:
                report.append(f"{action} {amount:g}{'°' if turn else ' m'}")
        body.stop()
        time.sleep(0.4)
        if closed:
            e = body.snapshot()
            h0 = math.radians(start["yaw_deg"])
            dx, dy = e["x"] - start["x"], e["y"] - start["y"]
            fwd, lat = dx * math.cos(h0) + dy * math.sin(h0), -dx * math.sin(h0) + dy * math.cos(h0)
            dyaw = math.degrees(wrap(math.radians(e["yaw_deg"]) - h0))
            tail = ("ATTENZIONE: scostamento dal richiesto, ricontrolla con look prima di proseguire." if deviated else "Non serve aggiustarlo.")
            return True, (f"eseguito: {'; '.join(report)}. In totale dall'inizio: avanti {fwd:+.2f} m, a sinistra {lat:+.2f} m, "
                          f"rotazione {dyaw:+.0f}° (+ = sinistra). {tail}")
        return True, f"eseguito a tempo come comandato ({'; '.join(report)}). Non serve ripeterlo o aggiustarlo; se vuoi controllare l'ambiente usa look"
