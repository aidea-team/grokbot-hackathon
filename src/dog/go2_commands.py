"""The command set of the Unitree Go2, shared by the real dog AND the mock. Same shape as commands.py (Go1).

What differs from the Go1 (see docs/hardware/robot-dog.md §1):
- the Go2 has sport-mode commands over WebRTC, not high-level UDP modes: one `Move(x, y, z)` velocity command that
  must be repeated, plus one-shot postures/tricks (StandUp, StandDown, RecoveryStand, Sit, RiseSit, Hello, Stretch,
  Dance1/2). So `strafe` (sideways) exists here and not on the Go1, and the tricks are one-shot;
- NOT exposed on purpose: `Damp` (drops the dog, CLAUDE.md: "mai Damp") and the flips (their api_id differs between
  firmwares, 1044 normal vs 2043 MCF: we cannot know which one we would trigger). Kill switch = StopMove, never Damp;
- no numeric limits, like the Go1 (guardrails are being rewritten by the team): only type/usability checks.
"""
from __future__ import annotations

import math

# tool -> driver.PRIMITIVES key (src/dog/go2_driver.py)
PRIMITIVE_TOOLS = {
    "stand_up": "stand_up", "lie_down": "lie_down", "recovery": "recovery",
    "sit": "sit", "rise_sit": "rise_sit", "hello": "hello", "stretch": "stretch",
}
TOOLS = ("walk", "strafe", "turn", "stand", *PRIMITIVE_TOOLS, "dance")
DEFAULT_WALK_SPEED = 0.3  # m/s
DEFAULT_TURN_RATE = 30.0  # deg/s


def _num(desc: str) -> dict:
    return {"type": "number", "description": desc}


def _secs(default: float) -> dict:
    return _num(f"Per quanti secondi aspettare che il movimento finisca (default {default:g})")


def tool_specs() -> dict[str, dict]:
    """name -> {description, parameters (JSON schema)}. Same for the mock and the real Go2."""
    def spec(desc, props=None, required=()):
        return {"description": desc,
                "parameters": {"type": "object", "properties": props or {}, "required": list(required)}}
    return {
        "walk": spec("Cammina in avanti (distanza positiva) o indietro (negativa), poi si ferma da solo. "
                     "A circuito aperto: velocità × tempo, senza correzioni.",
                     {"distance_m": _num("Metri da percorrere, negativo = indietro"),
                      "speed_mps": _num(f"Velocità in m/s (default {DEFAULT_WALK_SPEED:g})")}, ("distance_m",)),
        "strafe": spec("Passo laterale senza girarti: distanza positiva = verso sinistra, negativa = verso destra. "
                       "A circuito aperto.",
                       {"distance_m": _num("Metri di spostamento laterale, positivo = sinistra, negativo = destra"),
                        "speed_mps": _num(f"Velocità in m/s (default {DEFAULT_WALK_SPEED:g})")}, ("distance_m",)),
        "turn": spec("Gira su sé stesso: gradi positivi = a sinistra, negativi = a destra.",
                     {"degrees": _num("Angolo in gradi"),
                      "rate_dps": _num(f"Velocità angolare in gradi/s (default {DEFAULT_TURN_RATE:g})")}, ("degrees",)),
        "stand": spec("Resta fermo in piedi per un secondo (per osservare senza muoverti)."),
        "stand_up": spec("Alzati in piedi (StandUp).", {"seconds": _secs(3)}),
        "lie_down": spec("Accucciati a terra con i motori attivi (StandDown).", {"seconds": _secs(3)}),
        "recovery": spec("Rialzati da caduto (RecoveryStand).", {"seconds": _secs(4)}),
        "sit": spec("Siediti sulle zampe posteriori (Sit).", {"seconds": _secs(3)}),
        "rise_sit": spec("Alzati dalla posizione seduta (RiseSit).", {"seconds": _secs(3)}),
        "hello": spec("Saluta alzando una zampa (Hello).", {"seconds": _secs(4)}),
        "stretch": spec("Fai stretching (Stretch).", {"seconds": _secs(5)}),
        "dance": spec("Balla (Dance1 o Dance2).",
                      {"style": _num("1 o 2 (default 1)"), "seconds": _secs(15)}),
    }


def validate_args(name: str, args) -> tuple[bool, str, dict]:
    """Type / usability check only. Returns (ok, reason, clean_args)."""
    if name not in TOOLS:
        return False, f"comando sconosciuto {name!r} (disponibili: {', '.join(TOOLS)})", {}
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return False, "gli argomenti devono essere un oggetto", {}
    accepted = {"walk": {"distance_m", "speed_mps"}, "strafe": {"distance_m", "speed_mps"},
                "turn": {"degrees", "rate_dps"}, "stand": set(), "dance": {"style", "seconds"}}.get(name, {"seconds"})
    for key, value in args.items():
        if key not in accepted:
            return False, f"{name}: argomento sconosciuto {key!r}", {}
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return False, f"{name}.{key}: deve essere un numero finito", {}
    if name == "stand":
        return True, "ok", {}
    if name in ("walk", "strafe"):
        if "distance_m" not in args:
            return False, f"{name}: manca distance_m", {}
        speed = float(args.get("speed_mps", DEFAULT_WALK_SPEED))
        if speed == 0 or float(args["distance_m"]) == 0:
            return False, f"{name}: distance_m e speed_mps non possono essere 0", {}
        return True, "ok", {"distance_m": float(args["distance_m"]), "speed_mps": abs(speed)}
    if name == "turn":
        if "degrees" not in args:
            return False, "turn: manca degrees", {}
        rate = float(args.get("rate_dps", DEFAULT_TURN_RATE))
        if rate == 0 or float(args["degrees"]) == 0:
            return False, "turn: degrees e rate_dps non possono essere 0", {}
        return True, "ok", {"degrees": float(args["degrees"]), "rate_dps": abs(rate)}
    clean = {}
    if "seconds" in args:
        if float(args["seconds"]) <= 0:
            return False, f"{name}: seconds deve essere > 0", {}
        clean["seconds"] = float(args["seconds"])
    if name == "dance":
        style = int(args.get("style", 1))
        if style not in (1, 2):
            return False, "dance: style deve essere 1 o 2", {}
        clean["style"] = float(style)
    return True, "ok", clean


def label(name: str, clean: dict) -> str:
    return f"{name}({', '.join(f'{k}={v:g}' for k, v in clean.items())})"


def execute(driver, name: str, clean: dict):
    """Run one validated command on a Go2 driver (Go2Driver or Go2MockDriver). Blocks until it is done.
    Returns the driver's WalkResult, or None for `stand`."""
    if name == "walk":
        vx = math.copysign(clean["speed_mps"], clean["distance_m"])
        return driver.walk(vx, 0.0, abs(clean["distance_m"]) / clean["speed_mps"])
    if name == "strafe":
        vy = math.copysign(clean["speed_mps"], clean["distance_m"])
        return driver.strafe(vy, abs(clean["distance_m"]) / clean["speed_mps"])
    if name == "turn":
        vyaw = math.copysign(math.radians(clean["rate_dps"]), clean["degrees"])
        return driver.walk(0.0, vyaw, abs(clean["degrees"]) / clean["rate_dps"])
    if name == "stand":  # stay still for 1 s
        t_end = driver.now() + 1.0
        while driver.now() < t_end and not driver.halt_event.is_set():
            driver.drive(0.0, 0.0)
            driver.sleep(driver.LOOP_DT)
        return None
    prim = f"dance{int(clean['style'])}" if name == "dance" else PRIMITIVE_TOOLS[name]
    return driver.primitive(prim, clean.get("seconds"))
