"""The dog's brain: a closed perception -> action loop driven by an OpenAI model.

A user message starts a mission. Each step: wait until the dog is still, take a camera frame, show the
model the frame + odometry + the log of previous steps, and let it reason and choose ONE atomic action
(a tool call) or `finish`. Execute it, look again, repeat. A new message sent while a mission runs is handed
to the running mission at its next step.

The body it drives is chosen by the RobotHub: the MuJoCo simulator (all of src/sim/dog_world.py's actions, no
safety layer, virtual world) or the real Go1 (only the whitelisted tools of real_body.RealBody, every command
checked by its deterministic validator, kill switch, watchdog). The agent never talks to hardware directly.

Progress is published as events (user / step / final / note / error) that the web UI polls.
"""
from __future__ import annotations

import base64
import copy
import json
import os
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

import cameras
from dog_world import ACTIONS
from real_body import DISARMED, HALTED, RealBody
from scene import describe

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "gpt-4o-mini"
LOG_STEPS = 15  # most recent steps shown in full to the model
HISTORY_MISSIONS = 8  # past missions (goal + final message) kept in the prompt
HIDDEN_ACTIONS = {"go_to"}  # blind long moves: the dog must navigate by sight, one atomic step at a time
MAX_EVENTS, MAX_FRAMES = 1000, 400

SYSTEM_PROMPT = """Sei un cane robot Unitree Go1 che vive in un simulatore 3D. Sai di essere un cane robot, ma sei \
molto intelligente: ragioni con precisione e ti muovi con metodo. Non recitare: niente versi (mai «bau»), niente \
personaggio, niente esclamazioni. Scrivi in modo sobrio e diretto, nella lingua dell'umano (di norma italiano).

Come lavori (ciclo percezione → azione):
- A ogni passo ricevi le immagini delle tue 3 telecamere (descritte sotto), l'odometria (posizione e orientamento \
stimati rispetto al punto di partenza), il log dei passi già fatti e l'obiettivo dell'umano.
- Scegli UNA sola azione atomica, chiamando un solo tool. Dopo l'esecuzione riceverai un'immagine nuova e deciderai \
il passo successivo. Non pianificare sequenze lunghe alla cieca.
- In ogni chiamata compila `thought`: 1-3 frasi con ciò che vedi, a che punto sei rispetto all'obiettivo e perché \
scegli quell'azione.
- Passi piccoli: walk di solito 0,3-1 m (anche meno vicino a un oggetto), turn di 15-45°. Per allinearti a un \
bersaglio: se è a sinistra nell'immagine gira a sinistra (gradi positivi), se è a destra gira a destra (negativi).
- Se l'immagine è vuota (solo pavimento e cielo, nessun oggetto riconoscibile) o hai perso il bersaglio, non \
camminare alla cieca: gira gradualmente (turn di 30-45°) guardando dopo ogni rotazione finché lo ritrovi. Se hai \
fatto un giro completo senza trovarlo, spostati (walk di 1-2 m in un'altra direzione) e ripeti. Usa odometria e log \
per ricordare cosa hai già visto e dove.
- Quando l'obiettivo è raggiunto, o se la richiesta è solo una domanda o una conversazione, chiama `finish` con un \
messaggio breve e fattuale (cosa hai fatto o visto). Se la richiesta è impossibile o ambigua, chiama `finish` e \
spiegalo.
- Il mondo ha fisica vera: gli oggetti sono solidi, quelli leggeri si spostano se li spingi o li urti, e quelli \
fissi ti bloccano. Puoi passare solo dove c'è davvero spazio (dentro un tunnel, sotto una barra bassa, attraverso \
un'apertura saltando con la traiettoria giusta) o saltarci sopra. Se un'azione ti fa urtare qualcosa il log lo \
segnala: non insistere nella stessa direzione, aggira l'ostacolo o cambia approccio. Un salto o un salto mortale che \
urta o atterra male ti fa cadere: il log dice «SEI CADUTO» e il comando successivo ti rialza da solo.
- Sei bloccato SOLO se il log lo dice (BLOCCATO / hai toccato un oggetto). Un oggetto che vedi ma che non hai \
toccato non ti blocca: non concludere che il passaggio è chiuso solo a vista. Non rimpicciolire i passi all'infinito: \
se la strada è libera avanza di 0,5-1 m; vicino a un oggetto avvicinati ma poi decidi (aggira, passa sotto/dentro, \
salta) invece di fare passi sempre più piccoli.
- Odometria: angoli in gradi, positivi verso sinistra (antiorario); +x è la direzione di partenza, +y è a sinistra."""

REAL_PROMPT = """Sei un cane robot Unitree Go1 REALE, in un museo, con persone intorno. Sai di essere un cane robot, \
sei molto intelligente e soprattutto prudente. Non recitare: niente versi (mai «bau»), niente personaggio, niente \
esclamazioni. Scrivi in modo sobrio e diretto, nella lingua dell'umano (di norma italiano).

Come lavori (ciclo percezione → azione):
- A ogni passo ricevi le immagini delle tue 3 telecamere (descritte sotto), l'odometria stimata, il log dei passi \
già fatti e l'obiettivo dell'umano. Scegli UNA sola azione atomica (un solo tool); dopo l'esecuzione riceverai un'immagine nuova.
- In ogni chiamata compila `thought`: 1-3 frasi con ciò che vedi, a che punto sei rispetto all'obiettivo e perché \
scegli quell'azione.
- Sei un robot VERO: ogni movimento ha conseguenze fisiche. Passi molto corti: walk al massimo 0,5 m (di solito \
0,2-0,3), turn al massimo 45°. Se vedi una persona, un bambino, un cavo, un gradino o un oggetto a meno di circa un \
metro davanti, NON avanzare: gira per aggirarlo oppure chiama `finish` e spiega.
- Hai solo walk, turn, stand e finish. Non puoi saltare, sdraiarti né fare altro: se te lo chiedono, chiama `finish` \
e spiega che non puoi.
- Un validatore esterno può rifiutare un comando (limiti, geofence, batteria, kill switch): leggi il motivo nel log, \
cambia piano e non insistere. Se il cane risulta fermato dal kill switch, chiama `finish`.
- L'odometria è a circuito aperto (velocità comandata × tempo): è una stima e può essere sbagliata. Fidati più della \
telecamera che dei numeri.
- Se l'immagine è vuota o hai perso il bersaglio, gira gradualmente (turn di 20-40°) guardando dopo ogni rotazione; \
non camminare alla cieca.
- Quando l'obiettivo è raggiunto, o se la richiesta è solo una domanda, chiama `finish` con un messaggio breve e \
fattuale. Se l'umano ti dice di fermarti, chiama `finish` subito.
- Odometria: angoli in gradi, positivi verso sinistra (antiorario); +x è la direzione iniziale, +y è a sinistra."""

MAP_PROMPT = """

Ricordi la mappa del posto in cui vivi (centro degli oggetti in coordinate di odometria):
"""

THOUGHT = {"type": "string",
           "description": "Ragionamento breve (1-3 frasi): cosa vedi, a che punto sei rispetto all'obiettivo, "
                          "perché scegli questa azione."}

FINISH_TOOL = {
    "type": "function",
    "name": "finish",
    "description": "Concludi la missione e rispondi all'umano: obiettivo raggiunto, domanda risposta, oppure "
                   "richiesta impossibile/ambigua (spiega perché).",
    "parameters": {"type": "object",
                   "properties": {"thought": THOUGHT,
                                  "message": {"type": "string",
                                              "description": "Messaggio breve e fattuale per l'umano."}},
                   "required": ["thought", "message"]},
}


def system_prompt(mode: str = "sim") -> str:
    """Same camera description in sim and real: only the body (and its safety rules) differs."""
    return _base_prompt(mode) + "\n\n" + cameras.prompt_block()


def _base_prompt(mode: str = "sim") -> str:
    """DOG_KNOWS_MAP=1 in .env also gives the simulated dog the map of the props (default: only its eyes)."""
    if mode == "real":
        return REAL_PROMPT
    prompt = SYSTEM_PROMPT
    if os.environ.get("DOG_KNOWS_MAP", "0") == "1":
        prompt += MAP_PROMPT + describe()
    return prompt


class AgentError(Exception):
    """A problem to show to the human in the chat (missing key, API error...)."""


def build_tools(mode: str = "sim") -> list[dict]:
    """Tool list for the model. Real mode: ONLY the whitelist of RealBody, with its limits in the schema."""
    specs = (RealBody.tool_specs() if mode == "real"
             else {n: s for n, s in ACTIONS.items() if n not in HIDDEN_ACTIONS})
    tools = []
    for name, spec in specs.items():
        params = copy.deepcopy(spec["parameters"])
        params["properties"] = {"thought": THOUGHT, **params["properties"]}
        params["required"] = ["thought", *params["required"]]
        tools.append({"type": "function", "name": name, "description": spec["description"], "parameters": params})
    return tools + [FINISH_TOOL]


def _image_part(jpeg: bytes) -> dict:
    return {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}


def _camera_parts(shots: dict[str, bytes | None]) -> list[dict]:
    """One labelled image per camera, always in the same order; a missing camera is said explicitly."""
    parts: list[dict] = []
    for c in cameras.CAMERAS:
        jpeg = shots.get(c.name)
        if jpeg is None:
            parts.append({"type": "input_text", "text": f"[cam{c.n} «{c.label}»: NON DISPONIBILE in questo passo]"})
        else:
            parts += [{"type": "input_text", "text": f"[cam{c.n} «{c.label}» ({c.name})]"}, _image_part(jpeg)]
    return parts


def _key_ok(key: str | None) -> bool:
    return bool(key) and "REPLACE" not in key.upper()


class DogAgent:
    def __init__(self, hub, log=None):
        self.hub = hub  # chat/hub.py RobotHub: decides whether the body is the simulator or the real dog
        self.log = log
        self._tools = {"sim": build_tools("sim"), "real": build_tools("real")}
        self._lock = threading.Lock()
        self._events: list[dict] = []
        self._next_id = 0
        self._frames: dict[int, bytes] = {}
        self._history: list[dict] = []
        self._inbox: list[str] = []
        self._running = False
        self._epoch = 0  # bumped by abort()/reset(): a stale mission thread exits silently
        self._phase, self._step = "idle", 0

    @property
    def sim(self):
        """The active body (simulator or real dog); both expose the same interface."""
        return self.hub.body

    # ---------------------------------------------------------------- public API (web threads)
    def send(self, text: str) -> None:
        """Start a mission, or hand the message to the running one. Raises AgentError (e.g. no key)."""
        load_dotenv(ROOT / ".env", override=True)  # pick up a key pasted into .env without restarting
        if not _key_ok(os.environ.get("OPENAI_API_KEY")):
            raise AgentError("Manca la chiave: metti la tua OPENAI_API_KEY nel file .env della repo "
                             "(ora c'è il placeholder sk-REPLACE_ME) e rimanda il messaggio. Non serve riavviare.")
        self._emit("user", text=text)
        with self._lock:
            if self._running:
                self._inbox.append(text)
                return
            self._running, epoch = True, self._epoch
        threading.Thread(target=self._run, args=(text, epoch), daemon=True, name="dog-mission").start()

    def abort(self) -> None:
        with self._lock:
            was_running = self._running
            self._epoch += 1
            self._running = False
            self._inbox.clear()
            self._phase, self._step = "idle", 0
        self.sim.clear()
        if was_running:
            self._emit("note", text="Interrotto.")

    def reset(self) -> None:
        self.abort()
        with self._lock:
            self._events.clear()
            self._frames.clear()
            self._history.clear()

    def events(self, after: int = 0) -> list[dict]:
        with self._lock:
            return [e for e in self._events if e["id"] > after]

    def frame(self, frame_id: int) -> bytes | None:
        with self._lock:
            return self._frames.get(frame_id)

    def status(self) -> dict:
        return {"running": self._running, "phase": self._phase, "step": self._step}

    # ---------------------------------------------------------------- the loop (mission thread)
    def _run(self, goal: str, epoch: int) -> None:
        try:
            self._mission(goal, epoch)
        except AgentError as e:
            self._emit("error", text=str(e), epoch=epoch)
        except Exception as e:  # keep the app alive whatever happens
            self._log("mission_crash", error=repr(e))
            self._emit("error", text=f"Errore imprevisto: {e}", epoch=epoch)
        finally:
            leftover: list[str] = []
            with self._lock:
                if self._epoch == epoch:
                    self._running, self._phase, self._step = False, "idle", 0
                    leftover, self._inbox = self._inbox, []  # a message that arrived as the mission was ending
                    self._running = bool(leftover)
            if leftover:
                threading.Thread(target=self._run, args=(" / ".join(leftover), epoch), daemon=True,
                                 name="dog-mission").start()

    def _mission(self, goal: str, epoch: int) -> None:
        from openai import OpenAI, OpenAIError

        model = os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL
        effort = os.environ.get("OPENAI_REASONING_EFFORT") or None  # reasoning models only
        mode = self.hub.mode  # fixed for the whole mission: switching mode aborts it
        if mode == "real":
            max_steps = int(os.environ.get("DOG_MAX_STEPS_REAL") or 20)  # step limit: the real dog gets fewer
            if self.hub.real.state in (DISARMED, HALTED):
                raise AgentError("Il cane vero non è armato (o è stato fermato dal kill switch): "
                                 "arma di nuovo dal pulsante REAL prima di dare comandi.")
        else:
            max_steps = int(os.environ.get("DOG_MAX_STEPS") or 40)
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ.get("OPENAI_BASE_URL") or None)
        goals = [goal]
        steps: list[str] = []
        final: str | None = None
        self._log("mission_start", goal=goal, mode=mode, model=model, effort=effort)

        for n in range(1, max_steps + 1):
            self._set_phase(epoch, "osservo", n)
            if not self._wait_idle(epoch):
                return
            shots = {c.name: self.sim.capture(camera=c.name) for c in cameras.CAMERAS}
            frame = shots["front"]  # the front camera is mandatory (it is also the chat thumbnail)
            if frame is None:
                raise AgentError("La telecamera del cane non risponde (sei sul Wi-Fi del cane? ffmpeg installato?)"
                                 if mode == "real" else "La telecamera del simulatore non risponde.")
            frame_id = self._store_frame(frame)
            with self._lock:
                notes, self._inbox = self._inbox, []
            goals += notes
            text = self._prompt(goals, notes, steps)

            self._set_phase(epoch, "ragiono", n)
            kwargs: dict = {"model": model, "instructions": system_prompt(mode), "tools": self._tools[mode],
                            "tool_choice": "required", "parallel_tool_calls": False,
                            "input": [{"role": "user", "content": [{"type": "input_text", "text": text},
                                                                   *_camera_parts(shots)]}]}
            if effort:
                kwargs["reasoning"] = {"effort": effort}
            t0 = time.monotonic()
            try:
                resp = client.responses.create(**kwargs)
            except OpenAIError as e:
                self._log("llm_error", error=repr(e))
                raise AgentError(f"Errore dall'API OpenAI: {e}") from e
            latency = round(time.monotonic() - t0, 2)
            if self._epoch != epoch:
                return

            calls = [o for o in resp.output if o.type == "function_call"]
            if not calls:  # the model answered in plain text: treat it as the final message
                final = resp.output_text or "(nessuna risposta)"
                self._emit("step", n=n, thought="", action="finish", frame=frame_id, epoch=epoch)
                break
            call = calls[0]
            try:
                args = json.loads(call.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            thought = str(args.pop("thought", "")).strip()

            if call.name == "finish":
                final = str(args.get("message") or thought or "Fatto.")
                self._emit("step", n=n, thought=thought, action="finish", frame=frame_id, epoch=epoch)
                self._log("step", n=n, action="finish", thought=thought, latency_s=latency)
                break

            before = self.sim.snapshot()
            result = self.sim.submit(call.name, args)
            label = result.get("queued") or call.name
            self._emit("step", n=n, thought=thought, action=label, frame=frame_id,
                       **({} if result["ok"] else {"error": result["error"]}), epoch=epoch)
            self._log("step", n=n, action=label, thought=thought, latency_s=latency, ok=result["ok"])
            if not result["ok"]:
                steps.append(f"{n}. «{thought}» → azione rifiutata ({result['error']})")
                continue
            self._set_phase(epoch, f"eseguo {label}", n)
            if not self._wait_idle(epoch):
                return
            after = self.sim.snapshot()
            body = self.sim
            hit, stuck, crash, fell = body.last_block, body.last_stuck, body.last_crash, body.last_fell
            feedback = []  # physical feedback from the simulator (the real dog has none of these flags)
            if crash:
                feedback.append("URTO IN SALTO: hai colpito un oggetto solido durante il salto")
            elif stuck:
                feedback.append("BLOCCATO: un oggetto solido ti impedisce di avanzare")
            elif hit:
                feedback.append("hai toccato un oggetto solido")
            if fell:
                feedback.append("SEI CADUTO (il prossimo comando ti rialza)")
            if feedback:
                self._emit("note", text=" · ".join(feedback).capitalize() + ".", epoch=epoch)
                self._log("physics_feedback", n=n, action=label, object=hit, stuck=stuck, crash=crash, fell=fell)
            steps.append(f"{n}. «{thought[:240]}» → {label} → odometria: x={after['x']} y={after['y']} "
                         f"yaw={after['yaw_deg']}° (prima: x={before['x']} y={before['y']} yaw={before['yaw_deg']}°)"
                         + "".join(f" → {f}" for f in feedback))
        else:
            final = f"Mi fermo dopo {max_steps} passi senza aver concluso."

        if self._epoch != epoch:
            return
        self._emit("final", text=final, epoch=epoch)
        with self._lock:
            self._history.append({"goal": " / ".join(goals), "final": final})
            del self._history[:-HISTORY_MISSIONS]
        self._log("mission_end", goal=goal, final=final, steps=len(steps))

    def _prompt(self, goals: list[str], notes: list[str], steps: list[str]) -> str:
        s = self.sim.snapshot()
        lines = []
        with self._lock:
            past = list(self._history)
        if past:
            lines.append("Conversazione precedente:")
            lines += [f"- Umano: {h['goal']}\n  Tu (finale): {h['final']}" for h in past]
            lines.append("")
        lines.append(f"Obiettivo dell'umano: {goals[0]}")
        if len(goals) > 1:
            lines.append("Messaggi successivi dell'umano durante la missione: " + " | ".join(goals[1:]))
        if notes:
            lines.append(f"NUOVI messaggi appena arrivati (tienine conto adesso): {' | '.join(notes)}")
        lines.append("")
        lines.append(f"Odometria{' STIMATA a circuito aperto' if s.get('estimated') else ''}: x={s['x']} m, "
                     f"y={s['y']} m, orientamento {s['yaw_deg']}° (0° = verso +x), postura: {s['posture']}.")
        if steps:
            omitted = max(0, len(steps) - LOG_STEPS)
            lines.append(f"\nPassi già fatti ({omitted} più vecchi omessi):" if omitted else "\nPassi già fatti:")
            lines += steps[-LOG_STEPS:]
        else:
            lines.append("\nNessun passo ancora fatto.")
        lines.append("\nLe immagini allegate sono le tue 3 telecamere adesso. Scegli il prossimo passo.")
        return "\n".join(lines)

    # ---------------------------------------------------------------- helpers
    def _wait_idle(self, epoch: int, timeout: float = 180.0) -> bool:
        deadline = time.monotonic() + timeout
        while not self.sim.is_idle():
            if self._epoch != epoch or time.monotonic() > deadline:
                return False
            time.sleep(0.05)
        return self._epoch == epoch

    def _set_phase(self, epoch: int, phase: str, step: int) -> None:
        if self._epoch == epoch:
            self._phase, self._step = phase, step

    def _store_frame(self, jpeg: bytes) -> int:
        with self._lock:
            self._next_id += 1
            fid = self._next_id
            self._frames[fid] = jpeg
            for old in sorted(self._frames)[:-MAX_FRAMES]:
                del self._frames[old]
        return fid

    def _emit(self, kind: str, epoch: int | None = None, **fields) -> None:
        with self._lock:
            if epoch is not None and epoch != self._epoch:
                return
            self._next_id += 1
            self._events.append({"id": self._next_id, "type": kind, "t": round(time.time(), 2), **fields})
            del self._events[:-MAX_EVENTS]

    def _log(self, kind: str, **fields) -> None:
        if self.log is not None:
            self.log.event(kind, **fields)
