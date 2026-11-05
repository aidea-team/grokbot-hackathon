"""The dog's brain: a closed perception -> action loop driven by an OpenAI model.

A user message starts a mission. Each step: wait until the dog is still, take a camera frame, show the
model the frame + odometry + the log of previous steps, and let it reason and choose ONE atomic action
(a tool call) or `finish`. Execute it, look again, repeat. A new message sent while a mission runs is handed
to the running mission at its next step.

The body it drives is chosen by the RobotHub: the MuJoCo simulator (driven with the same Go1 commands as the real dog, no
safety layer, virtual world) or the real Go1 (the same commands as the simulator, every command
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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

import cameras
import jev
import llm_provider
import commands
import go2_commands
from real_body import DISARMED, HALTED, RealBody
from scene import describe
from settings import Settings, SettingsStore

ROOT = Path(__file__).resolve().parents[2]
HISTORY_MISSIONS = 8  # past missions (goal + final message) kept in the prompt
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
- Passi piccoli: walk di solito 0,3-1 m (anche meno vicino a un oggetto; per i tratti lunghi alza speed_mps fino a circa 0,8), turn di 15-45°. Per allinearti a un \
bersaglio: se è a sinistra nell'immagine gira a sinistra (gradi positivi), se è a destra gira a destra (negativi).
- Se l'immagine è vuota (solo pavimento e cielo, nessun oggetto riconoscibile) o hai perso il bersaglio, non \
camminare alla cieca: gira gradualmente (turn di 30-45°) guardando dopo ogni rotazione finché lo ritrovi. Se hai \
fatto un giro completo senza trovarlo, spostati (walk di 1-2 m in un'altra direzione) e ripeti. Usa odometria e log \
per ricordare cosa hai già visto e dove.
- Quando l'obiettivo è raggiunto, o se la richiesta è solo una domanda o una conversazione, chiama `finish` con un \
messaggio breve e fattuale (cosa hai fatto o visto). Se la richiesta è impossibile o ambigua, chiama `finish` e \
spiegalo.
- Per «salta» / «fai un salto» chiama `jump_yaw`: è il salto del Go1 (sul posto, con mezza giravolta). Non rifiutare \
un salto perché il Go1 non ha un salto «semplice»: `jump_yaw` è quello. Il salto mortale (`backflip`) è solo per \
richieste esplicite. Se hai ostacoli vicini valuta dalle immagini, ma non rifiutare un comando che hai.
- Il mondo ha fisica vera: gli oggetti sono solidi, quelli leggeri si spostano se li spingi o li urti, e quelli \
fissi ti bloccano. Puoi passare solo dove c'è davvero spazio. Se un'azione ti fa urtare qualcosa il log lo segnala: non insistere \
nella stessa direzione, aggira l'ostacolo o cambia approccio. Comandi e movimento sono gli stessi del cane vero e a \
circuito aperto (velocità × tempo): walk e turn non correggono la rotta e, da sdraiato o da caduto, non fanno nulla. \
Se il log dice «SEI CADUTO» usa `recovery`, se sei sdraiato `stand_up`. Un salto mortale che urta o atterra male ti \
fa cadere davvero.
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
- Sei un robot VERO: ogni movimento ha conseguenze fisiche. Se vedi una persona, un bambino, un cavo, un gradino o un oggetto a meno di circa un \
metro davanti, NON avanzare: gira per aggirarlo oppure chiama `finish` e spiega.
- Hai tutti i tool elencati (walk, turn, salti, flip, balli...) più finish. Un comando può comunque essere rifiutato \
(argomenti non validi, cane fermato dal kill switch): leggi il motivo nel log, cambia piano e non insistere. Se il cane risulta fermato dal kill switch, chiama `finish`.
- Per «salta» chiama `jump_yaw` (il salto del Go1, sul posto con mezza giravolta); `backflip` solo se richiesto \
esplicitamente. Se vedi persone o ostacoli a meno di un metro, chiedi/spiega invece di saltare.
- L'odometria è a circuito aperto (velocità comandata × tempo): è una stima e può essere sbagliata. Fidati più della \
telecamera che dei numeri.
- Se l'immagine è vuota o hai perso il bersaglio, gira gradualmente (turn di 20-40°) guardando dopo ogni rotazione; \
non camminare alla cieca.
- Quando l'obiettivo è raggiunto, o se la richiesta è solo una domanda, chiama `finish` con un messaggio breve e \
fattuale. Se l'umano ti dice di fermarti, chiama `finish` subito.
- Odometria: angoli in gradi, positivi verso sinistra (antiorario); +x è la direzione iniziale, +y è a sinistra."""

GO2_PROMPT = """Sei un cane robot Unitree Go2{where}. Sai di essere un cane robot, sei molto intelligente e soprattutto \
prudente. Non recitare: niente versi (mai «bau»), niente personaggio, niente esclamazioni. Scrivi in modo sobrio e \
diretto, nella lingua dell'umano (di norma italiano).

Come lavori (ciclo percezione → azione):
- A ogni passo ricevi l'immagine della tua telecamera frontale (descritta sotto), l'odometria stimata, il log dei passi \
già fatti e l'obiettivo dell'umano. Scegli UNA sola azione atomica (un solo tool); dopo l'esecuzione riceverai un'immagine nuova.
- In ogni chiamata compila `thought`: 1-3 frasi con ciò che vedi, a che punto sei rispetto all'obiettivo e perché \
scegli quell'azione.
- Hai: walk (avanti/indietro), strafe (passo laterale senza girarti), turn, stand, e i movimenti stand_up, lie_down, \
recovery, sit, rise_sit, hello, stretch, dance, più finish. Non hai salti né flip. Un comando può essere rifiutato \
(argomenti non validi, cane fermato dal kill switch): leggi il motivo nel log, cambia piano e non insistere. Se il cane \
risulta fermato dal kill switch, chiama `finish`.
- Prima di camminare assicurati di essere in piedi: se l'ultimo movimento ti ha lasciato seduto o accucciato, usa \
stand_up (o rise_sit) prima di walk/strafe/turn.
{safety}- L'odometria è a circuito aperto (velocità comandata × tempo): è una stima e può essere sbagliata. Fidati più della \
telecamera che dei numeri.
- Se l'immagine è vuota o hai perso il bersaglio, gira gradualmente (turn di 20-40°) guardando dopo ogni rotazione; \
non camminare alla cieca.
- Quando l'obiettivo è raggiunto, o se la richiesta è solo una domanda, chiama `finish` con un messaggio breve e \
fattuale. Se l'umano ti dice di fermarti, chiama `finish` subito.
- Odometria: angoli in gradi, positivi verso sinistra (antiorario); +x è la direzione iniziale, +y è a sinistra."""

GO2_REAL_SAFETY = """- Sei un robot VERO, in un luogo con persone intorno: ogni movimento ha conseguenze fisiche. Se vedi una persona, un \
bambino, un cavo, un gradino o un oggetto a meno di circa un metro davanti, NON avanzare: aggira o chiama `finish` e spiega.
"""
GO2_MOCK_SAFETY = """- Sei in modalità prova, senza hardware: l'immagine è una vista dall'alto SINTETICA (una griglia da 0,5 m, un anello \
verde sull'origine, tu sei il triangolo viola con il muso in alto), non una telecamera vera. Non ci sono ostacoli: serve \
solo a provare i comandi e l'odometria.
"""
GO2_CAM = ("Hai 1 telecamera, quella frontale (cam1 «davanti» (front)): sul muso, guarda dritto davanti a te (lungo +x, "
           "la direzione in cui cammini). Non hai telecamere laterali né verso il basso.")

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


def cam_block(cfg: Settings | None = None, robot: str = "go1") -> str:
    """Camera paragraph; if some cameras are switched off in the settings, say which ones the model gets."""
    if robot == "go2":
        return GO2_CAM  # a single camera: nothing to switch off
    block = cameras.prompt_block()
    if cfg is not None and len(cfg.cams) < len(cameras.CAMERAS):
        got = ", ".join(f"cam{c.n} «{c.label}»" for c in cameras.CAMERAS if c.name in cfg.cams)
        block += (f"\nIN QUESTA SESSIONE (per velocità) ricevi SOLO: {got}. Le altre telecamere non ti vengono "
                  "inviate: non dire che sono guaste, semplicemente non le hai.")
    return block


def system_prompt(mode: str = "sim", cfg: Settings | None = None, robot: str = "go1") -> str:
    """Same camera description in sim and real: only the body (and its safety rules) differs."""
    prompt = _base_prompt(mode, robot) + "\n\n" + cam_block(cfg, robot)
    if cfg is not None and not cfg.llm_thought:
        prompt += "\n\nNon compilare `thought` (non esiste): chiama direttamente il tool."
    return prompt


def _base_prompt(mode: str = "sim", robot: str = "go1") -> str:
    """DOG_KNOWS_MAP=1 in .env also gives the simulated dog the map of the props (default: only its eyes)."""
    if robot == "go2":
        real = mode == "real"
        return GO2_PROMPT.format(where=" REALE, in un museo" if real else " in modalità prova (mock)",
                                 safety=GO2_REAL_SAFETY if real else GO2_MOCK_SAFETY)
    if mode == "real":
        return REAL_PROMPT
    prompt = SYSTEM_PROMPT
    if os.environ.get("DOG_KNOWS_MAP", "0") == "1":
        prompt += MAP_PROMPT + describe()
    return prompt


class AgentError(Exception):
    """A problem to show to the human in the chat (missing key, API error...)."""


def build_tools(mode: str = "sim", thought: bool = True, robot: str = "go1") -> list[dict]:
    """Tool list for the model: the command set of the robot (src/dog/commands.py = Go1, go2_commands.py = Go2),
    identical in sim and real."""
    specs = (go2_commands if robot == "go2" else commands).tool_specs()  # the SAME commands in mock and real
    tools = []
    for name, spec in specs.items():
        params = copy.deepcopy(spec["parameters"])
        if thought:
            params["properties"] = {"thought": THOUGHT, **params["properties"]}
            params["required"] = ["thought", *params["required"]]
        tools.append({"type": "function", "name": name, "description": spec["description"], "parameters": params})
    finish = FINISH_TOOL
    if not thought:
        finish = {**FINISH_TOOL, "parameters": {**FINISH_TOOL["parameters"], "required": ["message"],
                                                 "properties": {"message": FINISH_TOOL["parameters"]["properties"]["message"]}}}
    return tools + [finish]


def _image_part(jpeg: bytes) -> dict:
    return {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()}


def _camera_parts(shots: dict[str, bytes | None]) -> list[dict]:
    """One labelled image per camera, always in the same order; a missing camera is said explicitly."""
    parts: list[dict] = []
    for c in cameras.CAMERAS:
        if c.name not in shots:  # switched off in the settings: not sent at all
            continue
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
        self.settings = SettingsStore(Path(log.path).parent / "settings.json" if log is not None else None)
        self._tool_cache: dict = {}
        self._pool = ThreadPoolExecutor(max_workers=len(cameras.CAMERAS), thread_name_prefix="cam")
        self._lock = threading.Lock()
        self._events: list[dict] = []
        self._next_id = 0
        self._frames: dict[int, bytes] = {}
        self._history: list[dict] = []
        self._inbox: list[str] = []
        self._running = False
        self._epoch = 0  # bumped by abort()/reset(): a stale mission thread exits silently
        self._phase, self._step = "idle", 0
        self.brain = "llm"  # "llm" = reasoning agent (Responses API); "jev" = OpenAI Decisions API (src/chat/jev.py)
        self.provider = llm_provider.default_provider()  # who backs the "llm" brain: "openai" or "grok" (src/llm_provider.py)

    def set_provider(self, provider: str) -> None:
        if provider not in llm_provider.PROVIDERS:
            raise AgentError(f"provider sconosciuto: {provider!r}")
        self.abort()  # a running mission keeps its model: switching ends it
        self.provider = provider

    def set_brain(self, brain: str) -> None:
        if brain not in ("llm", "jev"):
            raise AgentError(f"brain sconosciuto: {brain!r}")
        if brain == "jev" and self.hub.robot == "go2":
            raise AgentError("JEV è tarato sul Go1 (azioni e angoli): per il Go2 usa il cervello LLM.")
        self.abort()  # a running mission keeps its brain: switching ends it
        self.brain = brain

    def _jev_tools(self, mode: str) -> dict[str, str]:
        """tool name -> description, from the same specs the LLM brain sees (so the whitelist is the same)."""
        specs = commands.tool_specs()
        return {**{n: s["description"] for n, s in specs.items()}, "finish": FINISH_TOOL["description"]}

    @property
    def sim(self):
        """The active body (simulator or real dog); both expose the same interface."""
        return self.hub.body

    # ---------------------------------------------------------------- public API (web threads)
    def send(self, text: str) -> None:
        """Start a mission, or hand the message to the running one. Raises AgentError (e.g. no key)."""
        load_dotenv(ROOT / ".env", override=True)  # pick up a key pasted into .env without restarting
        lc = llm_provider.config(self.provider)
        if self.brain == "llm" and not llm_provider.key_ok(lc):
            raise AgentError(llm_provider.missing_key_message(lc) + " Non serve riavviare.")
        if self.brain == "jev" and not _key_ok(os.environ.get("OPENAI_API_KEY")):
            raise AgentError("JEV usa la Decisions API di OpenAI: metti OPENAI_API_KEY nel file .env della repo.")
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
        lc = llm_provider.config(self.provider)
        return {"running": self._running, "phase": self._phase, "step": self._step, "brain": self.brain,
                "provider": self.provider, "model": lc.model}

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
        from openai import OpenAIError

        provider = self.provider  # fixed for the whole mission: switching provider aborts it
        lc = llm_provider.config(provider)
        model = lc.model
        env_effort = lc.effort  # reasoning models only
        actual_mode = self.hub.mode  # fixed for the whole mission: switching mode aborts it
        mode = "real" if actual_mode in ("real", "both") else "sim"  # "both" is the real dog (+ a simulator mirror)
        robot = self.hub.robot  # fixed for the whole mission too: switching robot aborts it
        brain = self.brain  # same: fixed for the mission
        if mode == "real":
            max_steps = int(os.environ.get("DOG_MAX_STEPS_REAL") or 20)  # step limit: the real dog gets fewer
            if self.hub.active_real.state in (DISARMED, HALTED):
                raise AgentError("Il cane vero non è armato (o è stato fermato dal kill switch): "
                                 "arma di nuovo dal pulsante REAL prima di dare comandi.")
        else:
            max_steps = int(os.environ.get("DOG_MAX_STEPS") or 40)
        client = llm_provider.make_client(lc)
        cfg = self.settings.get()
        if brain == "jev" and cfg.jev_session:
            jev.prewarm()  # open the TLS connection before the first decision
        goals = [goal]
        steps: list[str] = []
        final: str | None = None
        totals = {"wait": 0.0, "cap": 0.0, "api": 0.0, "exec": 0.0}
        self._log("mission_start", goal=goal, mode=mode, robot=robot, body=actual_mode, provider=provider, model=model, effort=cfg.llm_effort or env_effort,
                  brain=brain, settings=asdict(cfg))

        for n in range(1, max_steps + 1):
            cfg = self.settings.get()  # live: changes from the settings dialog apply at the next step
            effort = cfg.llm_effort or env_effort
            self._set_phase(epoch, "osservo", n)
            t_start = time.monotonic()
            if not self._wait_idle(epoch):
                return
            t_wait = time.monotonic() - t_start
            t0 = time.monotonic()
            shots = self._capture_all(cfg, mode, robot)
            t_cap = time.monotonic() - t0
            frame = shots["front"]  # the front camera is mandatory (it is also the chat thumbnail)
            if frame is None:
                raise AgentError("La telecamera del cane non risponde (sei sul Wi-Fi del cane? ffmpeg installato?)"
                                 if mode == "real" and robot == "go1" else
                                 "La telecamera del Go2 non risponde (WebRTC collegato? la telecamera parte con l'arm)."
                                 if mode == "real" else "La telecamera del simulatore non risponde.")
            frame_id = self._store_frame(frame)
            with self._lock:
                notes, self._inbox = self._inbox, []
            goals += notes
            text = self._prompt(goals, notes, steps, cfg)

            self._set_phase(epoch, "ragiono", n)
            t0 = time.monotonic()
            dec = None
            if brain == "jev":
                multi = cfg.jev_multi and mode == "sim"  # a blind 2nd move is never allowed on the real dog
                try:
                    dec = jev.decide([{"type": "input_text", "text": text}, *_camera_parts(shots)],
                                     self._jev_tools(mode), mode, reuse_session=cfg.jev_session,
                                     reduced=cfg.jev_reduced_angles, multi=multi, cam_block=cam_block(cfg))
                except jev.JevError as e:
                    self._log("llm_error", error=repr(e), brain="jev")
                    raise AgentError(f"Errore dalla Decisions API (JEV): {e}") from e
                name, args, thought = dec.name, dict(dec.args), dec.thought
                if name == "finish":
                    args["message"] = (self._compose_final(client, model, effort, mode, text, shots, cfg)
                                       if cfg.jev_finish_llm
                                       else "Obiettivo concluso (JEV sceglie solo azioni: non scrive testo).")
                extra = {"confidence": dec.confidence}
            else:
                kwargs: dict = {"model": model, "instructions": system_prompt(mode, cfg, robot),
                                "tools": self._tools_for(mode, cfg.llm_thought, robot),
                                "tool_choice": "required", "parallel_tool_calls": False,
                                "input": [{"role": "user", "content": [{"type": "input_text", "text": text},
                                                                       *_camera_parts(shots)]}]}
                if effort:
                    kwargs["reasoning"] = {"effort": effort}
                try:
                    resp = client.responses.create(**kwargs)
                except OpenAIError as e:
                    self._log("llm_error", error=repr(e))
                    raise AgentError(f"Errore dall'API {lc.label}: {e}") from e
                calls = [o for o in resp.output if o.type == "function_call"]
                if calls:
                    try:
                        args = json.loads(calls[0].arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    name, thought, extra = calls[0].name, str(args.pop("thought", "")).strip(), {}
                else:  # the model answered in plain text: treat it as the final message
                    name, args, thought, extra = "finish", {"message": resp.output_text or "(nessuna risposta)"}, "", {}
            t_api = time.monotonic() - t0
            latency = round(t_api, 2)
            if self._epoch != epoch:
                return

            timing = {"wait": t_wait, "cap": t_cap, "api": t_api, "exec": 0.0}

            def close_step(label: str = "") -> None:
                """Timing of this step: JSONL + a `timing` event the UI attaches to the step."""
                timing["exec"] = timing["exec"] if label else 0.0
                for k in totals:
                    totals[k] += timing[k]
                t = {k: round(v, 2) for k, v in timing.items()}
                t["total"] = round(sum(timing.values()), 2)
                self._emit("timing", n=n, brain=brain, epoch=epoch, **t)
                self._log("step_timing", n=n, brain=brain, **t)

            if name == "finish":
                final = str(args.get("message") or thought or "Fatto.")
                self._emit("step", n=n, thought=thought, action="finish", frame=frame_id, epoch=epoch)
                self._log("step", n=n, action="finish", thought=thought, latency_s=latency, brain=brain, **extra)
                close_step()
                break

            before = self.sim.snapshot()
            result = self.sim.submit(name, args)
            label = result.get("queued") or name
            self._emit("step", n=n, thought=thought, action=label, frame=frame_id,
                       **({} if result["ok"] else {"error": result["error"]}), epoch=epoch)
            self._log("step", n=n, action=label, thought=thought, latency_s=latency, ok=result["ok"], brain=brain, **extra)
            if not result["ok"]:
                steps.append(f"{n}. «{thought}» → azione rifiutata ({result['error']})")
                close_step()
                continue
            t0 = time.monotonic()
            alive, after, feedback = self._observe(epoch, n, label)
            if not alive:
                return
            steps.append(f"{n}. «{thought[:240]}» → {label} → odometria: x={after['x']} y={after['y']} "
                         f"yaw={after['yaw_deg']}° (prima: x={before['x']} y={before['y']} yaw={before['yaw_deg']}°)"
                         + "".join(f" → {f}" for f in feedback))

            # JEV only: a 2nd action from the same call, when both are confident and the 1st went smoothly
            sec = dec.second if dec is not None else None
            if (sec is not None and not feedback and dec.confidence >= cfg.jev_multi_min_conf
                    and sec.confidence >= cfg.jev_multi_min_conf and self._epoch == epoch):
                before2 = after
                r2 = self.sim.submit(sec.name, sec.args)
                label2 = r2.get("queued") or sec.name
                self._emit("step", n=n, thought=sec.thought, action=label2, frame=frame_id,
                           **({} if r2["ok"] else {"error": r2["error"]}), epoch=epoch)
                self._log("step", n=n, part=2, action=label2, thought=sec.thought, ok=r2["ok"], brain=brain,
                          confidence=sec.confidence)
                if r2["ok"]:
                    alive, after2, fb2 = self._observe(epoch, n, label2)
                    if not alive:
                        return
                    steps.append(f"{n}b. «{sec.thought}» → {label2} → odometria: x={after2['x']} y={after2['y']} "
                                 f"yaw={after2['yaw_deg']}° (prima: x={before2['x']} y={before2['y']} "
                                 f"yaw={before2['yaw_deg']}°)" + "".join(f" → {f}" for f in fb2))
            timing["exec"] = time.monotonic() - t0
            close_step(label)
        else:
            final = f"Mi fermo dopo {max_steps} passi senza aver concluso."

        if self._epoch != epoch:
            return
        self._emit("final", text=final, epoch=epoch)
        with self._lock:
            self._history.append({"goal": " / ".join(goals), "final": final})
            del self._history[:-HISTORY_MISSIONS]
        n_steps = max(1, len(steps))
        self._log("mission_end", goal=goal, final=final, steps=len(steps), brain=brain,
                  avg_s={k: round(v / n_steps, 2) for k, v in totals.items()},
                  total_s={k: round(v, 2) for k, v in totals.items()})

    def _observe(self, epoch: int, n: int, label: str) -> tuple[bool, dict, list[str]]:
        """Wait for the action to finish, then read the physical feedback (the real dog has none of these flags)."""
        self._set_phase(epoch, f"eseguo {label}", n)
        if not self._wait_idle(epoch):
            return False, {}, []
        after = self.sim.snapshot()
        body = self.sim
        hit, stuck, crash, fell = body.last_block, body.last_stuck, body.last_crash, body.last_fell
        feedback = []
        if crash:
            feedback.append("URTO IN SALTO: hai colpito un oggetto solido durante il salto")
        elif stuck:
            feedback.append("BLOCCATO: un oggetto solido ti impedisce di avanzare")
        elif hit:
            feedback.append("hai toccato un oggetto solido")
        if fell:
            feedback.append("SEI CADUTO (usa recovery per rialzarti)")
        if feedback:
            self._emit("note", text=" · ".join(feedback).capitalize() + ".", epoch=epoch)
            self._log("physics_feedback", n=n, action=label, object=hit, stuck=stuck, crash=crash, fell=fell)
        return True, after, feedback

    def _capture_all(self, cfg: Settings, mode: str, robot: str = "go1") -> dict[str, bytes | None]:
        """Frames of the enabled cameras; in parallel (default) the step waits for the slowest one, not the sum."""
        names = ["front"] if robot == "go2" else [c.name for c in cameras.CAMERAS if c.name in cfg.cams]
        w, h = cfg.width_height()
        if hasattr(self.hub.active_sim, "jpeg_quality"):
            self.hub.active_sim.jpeg_quality = cfg.jpeg_quality
        grab = lambda name: self.sim.capture(w, h, camera=name)  # noqa: E731  (the real body ignores w/h)
        if cfg.parallel_capture and len(names) > 1:
            return dict(zip(names, self._pool.map(grab, names)))
        return {name: grab(name) for name in names}

    def _tools_for(self, mode: str, thought: bool, robot: str = "go1") -> list[dict]:
        key = (mode, thought, robot)
        if key not in self._tool_cache:
            self._tool_cache[key] = build_tools(mode, thought, robot)
        return self._tool_cache[key]

    def _compose_final(self, client, model: str, effort: str | None, mode: str, text: str,
                       shots: dict, cfg: Settings) -> str:
        """JEV cannot write text: one LLM call (no tools) words the final answer for the human."""
        fallback = "Obiettivo concluso (JEV sceglie solo azioni: non scrive testo)."
        kwargs: dict = {"model": model, "instructions": system_prompt(mode, cfg),
                        "input": [{"role": "user", "content": [
                            {"type": "input_text", "text": text + "\n\nLa missione è conclusa (o la richiesta è solo "
                             "una domanda): rispondi all'umano con un messaggio breve e fattuale. Non chiamare tool."},
                            *_camera_parts(shots)]}]}
        if effort:
            kwargs["reasoning"] = {"effort": effort}
        try:
            return client.responses.create(**kwargs).output_text or fallback
        except Exception as e:  # never lose the mission over the final message
            self._log("llm_error", error=repr(e), where="compose_final")
            return fallback

    def _prompt(self, goals: list[str], notes: list[str], steps: list[str], cfg: Settings) -> str:
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
            omitted = max(0, len(steps) - cfg.llm_log_steps)
            lines.append(f"\nPassi già fatti ({omitted} più vecchi omessi):" if omitted else "\nPassi già fatti:")
            lines += steps[-cfg.llm_log_steps:]
        else:
            lines.append("\nNessun passo ancora fatto.")
        lines.append("\nLe immagini allegate sono le tue telecamere adesso. Scegli il prossimo passo.")
        return "\n".join(lines)

    # ---------------------------------------------------------------- helpers
    def _wait_idle(self, epoch: int, timeout: float = 180.0) -> bool:
        deadline = time.monotonic() + timeout
        while not self.sim.is_idle():
            if self._epoch != epoch or time.monotonic() > deadline:
                return False
            time.sleep(0.01)
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
