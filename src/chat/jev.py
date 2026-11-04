"""JEV brain: one fast call to OpenAI's Decisions API (POST /v1/decisions) instead of a reasoning agent loop.

The Decisions API does not write text and has no free-form arguments: it answers bounded questions (choice /
predicate / score) with probabilities, about text + images, on the same input, in ONE request. So a step is:

  - question `action`: which tool (walk / turn / stand / ... / finish) -> the tool call;
  - question `turn_degrees`, `walk_distance_m`: a choice among a few discrete values -> the numeric argument.

All questions are asked every step (they are cheap); only the ones relevant to the chosen action are used.
Everything the model proposes still goes through the same body / validator as the LLM brain (real_body.py).
Docs: https://developers.openai.com/api/docs/guides/decisions (checked 2026-11-04: model gpt-6-luna, inline
base64 data URLs for images, up to 400 questions per request).
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field

import requests


DEFAULT_URL = "https://api.openai.com/v1/decisions"
DEFAULT_MODEL = "gpt-6-luna"

TURN_CHOICES = {"sim": [-90, -45, -30, -15, 15, 30, 45, 90], "real": [-45, -30, -15, 15, 30, 45]}
TURN_REDUCED = [-45, -30, -15, 15, 30, 45]
WALK_CHOICES = {"sim": [-0.3, 0.3, 0.6, 1.0, 1.5], "real": [-0.3, 0.2, 0.3, 0.5]}

PREAMBLE = """Sei il cervello di un cane robot Unitree Go1. Ogni passo scegli UNA azione atomica in base alle immagini \
delle tue telecamere, all'odometria e all'obiettivo dell'umano. Passi piccoli: dopo ogni azione vedrai un'immagine nuova.
Se l'obiettivo è raggiunto, o la richiesta è solo una domanda o è impossibile, scegli `finish`.
Se hai perso il bersaglio (immagine vuota) gira per cercarlo, non camminare alla cieca. Se vedi una persona, un \
cavo o un oggetto a meno di circa un metro davanti, non avanzare: gira per aggirarlo o scegli `finish`.
Per allinearti a un bersaglio: se è a sinistra nell'immagine gira a sinistra (gradi positivi), se è a destra gira \
a destra (negativi). Angoli positivi = sinistra (antiorario)."""


class JevError(Exception):
    """The Decisions API call failed (network, HTTP error, malformed answer)."""


@dataclass
class Decision:
    name: str
    args: dict
    thought: str
    confidence: float
    raw: dict = field(default_factory=dict)  # the full answers, for the JSONL log
    second: "Decision | None" = None  # optional 2nd action (turn/walk) from the same call


def _param_questions(tools: dict[str, str], mode: str, reduced: bool, sfx: str, when: str) -> list[dict]:
    qs = []
    if "turn" in tools:
        angles = TURN_REDUCED if (reduced or mode == "real") else TURN_CHOICES[mode]
        qs.append({"type": "choice", "name": "turn_degrees" + sfx,
                   "instructions": f"Se {when} fosse `turn`: di quanti gradi girare? Positivo = sinistra, negativo = "
                                   "destra. Scegli l'angolo che allinea il cane al bersaglio (o per cercarlo).",
                   "choices": [{"value": str(v), "description": "a sinistra" if v > 0 else "a destra"}
                               for v in angles]})
    if "walk" in tools:
        qs.append({"type": "choice", "name": "walk_distance_m" + sfx,
                   "instructions": f"Se {when} fosse `walk`: quanti metri percorrere? Negativo = indietro. Vicino a "
                                   "un oggetto scegli poco, con la strada libera di più.",
                   "choices": [{"value": str(v), "description": "indietro" if v < 0 else "in avanti"}
                               for v in WALK_CHOICES[mode]]})
    return qs


def _questions(tools: dict[str, str], mode: str, reduced: bool = False, multi: bool = False) -> list[dict]:
    """`tools`: tool name -> description (everything the body accepts, plus finish)."""
    qs = [{"type": "choice", "name": "action",
           "instructions": "Qual è l'azione migliore da fare ADESSO per l'obiettivo dell'umano?",
           "choices": [{"value": n, "description": d} for n, d in tools.items()]}]
    qs += _param_questions(tools, mode, reduced, "", "l'azione")
    if multi and ("turn" in tools or "walk" in tools):
        second = [n for n in ("turn", "walk") if n in tools]
        qs.append({"type": "choice", "name": "action_2",
                   "instructions": "Subito DOPO la prima azione, senza rivedere le immagini, c'è una seconda azione "
                                   "sicura e certa da fare (per esempio un walk dopo aver allineato il bersaglio)? "
                                   "Scegli `none` se prima devi rivedere cosa succede.",
                   "choices": [{"value": "none", "description": "nessuna: rivedo le immagini prima"},
                               *[{"value": n, "description": tools[n]} for n in second]]})
        qs += _param_questions({n: tools[n] for n in second}, mode, reduced, "_2", "la seconda azione")
    return qs


_session: requests.Session | None = None
_session_lock = threading.Lock()


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}"}


def _get_session() -> requests.Session:
    global _session
    with _session_lock:
        if _session is None:
            _session = requests.Session()
        return _session


def prewarm() -> None:
    """Open the TLS connection now (a cheap GET), so the first decision does not pay for the handshake."""
    try:
        url = (os.environ.get("JEV_URL") or DEFAULT_URL).rsplit("/decisions", 1)[0] + "/models"
        _get_session().get(url, headers=_headers(), timeout=5)
    except requests.RequestException:
        pass


def _args(name: str, answers: dict, sfx: str, parts: list[str]) -> dict:
    if name == "turn" and "turn_degrees" + sfx in answers:
        a = answers["turn_degrees" + sfx]
        parts.append(f"{a['choice']}° ({a.get('confidence', 0):.2f})")
        return {"degrees": float(a["choice"])}
    if name == "walk" and "walk_distance_m" + sfx in answers:
        a = answers["walk_distance_m" + sfx]
        parts.append(f"{a['choice']} m ({a.get('confidence', 0):.2f})")
        return {"distance_m": float(a["choice"])}
    return {}


def decide(content: list[dict], tools: dict[str, str], mode: str, timeout: float = 30.0, *,
           reuse_session: bool = True, reduced: bool = False, multi: bool = False,
           cam_block: str = "") -> Decision:
    """`content`: input_text / input_image parts (goal, odometry, log, camera frames)."""
    body = {"model": os.environ.get("JEV_MODEL") or DEFAULT_MODEL,
            "input": [{"role": "user", "content": [{"type": "input_text", "text": PREAMBLE + "\n\n" + cam_block},
                                                   *content]}],
            "questions": _questions(tools, mode, reduced, multi)}
    post = _get_session().post if reuse_session else requests.post
    try:
        r = post(os.environ.get("JEV_URL") or DEFAULT_URL, json=body, timeout=timeout, headers=_headers())
    except requests.RequestException as e:
        raise JevError(f"Decisions API non raggiungibile: {e}") from e
    if r.status_code != 200:
        raise JevError(f"Decisions API HTTP {r.status_code}: {r.text[:300]}")
    try:
        answers = {a["name"]: a for a in r.json()["answers"]}
        act = answers["action"]
        name = act["choice"]
    except (ValueError, KeyError, TypeError) as e:
        raise JevError(f"Risposta Decisions API inattesa: {r.text[:300]}") from e
    if name not in tools:
        raise JevError(f"Decisions API ha scelto un'azione sconosciuta: {name!r}")

    parts = [f"{name} ({act.get('confidence', 0):.2f})"]
    args = _args(name, answers, "", parts)
    dec = Decision(name=name, args=args, thought="", confidence=float(act.get("confidence", 0)), raw=answers)
    a2 = answers.get("action_2")
    if multi and a2 and a2.get("choice") in ("turn", "walk") and name not in ("finish",):
        parts2 = [f"{a2['choice']} ({a2.get('confidence', 0):.2f})"]
        args2 = _args(a2["choice"], answers, "_2", parts2)
        dec.second = Decision(name=a2["choice"], args=args2, thought="JEV 2/2: " + " · ".join(parts2),
                              confidence=float(a2.get("confidence", 0)))
    dec.thought = "JEV: " + " · ".join(parts)
    return dec
