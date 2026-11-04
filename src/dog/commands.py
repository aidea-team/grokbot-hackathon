"""The command set of the Go1, shared by the real dog AND the simulator.

One definition of the tools the model sees, of how their arguments are checked and of how each tool turns into
driver calls: `driver.walk(vx, vyaw, seconds)` for walk / turn, `driver.drive(0, 0)` for stand, and
`driver.primitive(name, seconds)` for the Go1 high-level modes (STAND_UP, STAND_DOWN, RECOVERY, BACKFLIP,
JUMPYAW, STRAIGHTHAND, DANCE1/2, DAMPING). RealBody runs these against Go1Driver, SimBody against SimDriver:
the simulator receives exactly the commands the dog would receive, and only the physics behind the driver differs.

No numeric limits (removed on purpose, see CLAUDE.md): arguments are only checked for type and for being usable.
"""
from __future__ import annotations

import math

PRIMITIVE_TOOLS = {  # tool -> driver.PRIMITIVES key
    "stand_up": "stand_up", "lie_down": "lie_down", "recovery": "recovery", "backflip": "backflip",
    "jump_yaw": "jump_yaw", "straight_hand": "straight_hand", "damping": "damping",
}
TOOLS = ("walk", "turn", "stand", *PRIMITIVE_TOOLS, "dance")
DEFAULT_WALK_SPEED = 0.2  # m/s
DEFAULT_TURN_RATE = 25.0  # deg/s


def _num(desc: str) -> dict:
    return {"type": "number", "description": desc}


def _secs(default: float) -> dict:
    return _num(f"Per quanti secondi tenere il comando attivo (default {default:g})")


def tool_specs() -> dict[str, dict]:
    """name -> {description, parameters (JSON schema)}. Same for the simulator and the real dog."""
    def spec(desc, props=None, required=()):
        return {"description": desc,
                "parameters": {"type": "object", "properties": props or {}, "required": list(required)}}
    return {
        "walk": spec("Cammina in avanti (distanza positiva) o indietro (negativa), poi si ferma da solo. "
                     "A circuito aperto: velocità × tempo, senza correzioni.",
                     {"distance_m": _num("Metri da percorrere, negativo = indietro"),
                      "speed_mps": _num(f"Velocità in m/s (default {DEFAULT_WALK_SPEED:g})")}, ("distance_m",)),
        "turn": spec("Gira su sé stesso: gradi positivi = a sinistra, negativi = a destra.",
                     {"degrees": _num("Angolo in gradi"),
                      "rate_dps": _num(f"Velocità angolare in gradi/s (default {DEFAULT_TURN_RATE:g})")}, ("degrees",)),
        "stand": spec("Resta fermo in piedi per un secondo (per osservare senza muoverti)."),
        "stand_up": spec("Alzati in piedi (modalità STAND_UP).", {"seconds": _secs(2)}),
        "lie_down": spec("Sdraiati (modalità STAND_DOWN).", {"seconds": _secs(3)}),
        "recovery": spec("Rialzati da caduto (modalità RECOVERY).", {"seconds": _secs(4)}),
        "backflip": spec("Salto mortale all'indietro (modalità BACKFLIP).", {"seconds": _secs(4)}),
        "jump_yaw": spec("Salto con giravolta in aria (modalità JUMPYAW).", {"seconds": _secs(4)}),
        "straight_hand": spec("Allunga la zampa anteriore (modalità STRAIGHTHAND).", {"seconds": _secs(4)}),
        "dance": spec("Balla (modalità DANCE1 o DANCE2).",
                      {"style": _num("1 o 2 (default 1)"), "seconds": _secs(15)}),
        "damping": spec("Spegne i motori: il cane si affloscia a terra (modalità DAMPING).", {"seconds": _secs(2)}),
    }


def validate_args(name: str, args) -> tuple[bool, str, dict]:
    """Type / usability check only. Returns (ok, reason, clean_args)."""
    if name not in TOOLS:
        return False, f"comando sconosciuto {name!r} (disponibili: {', '.join(TOOLS)})", {}
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return False, "gli argomenti devono essere un oggetto", {}
    accepted = {"walk": {"distance_m", "speed_mps"}, "turn": {"degrees", "rate_dps"}, "stand": set(),
                "dance": {"style", "seconds"}}.get(name, {"seconds"})
    for key, value in args.items():
        if key not in accepted:
            return False, f"{name}: argomento sconosciuto {key!r}", {}
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return False, f"{name}.{key}: deve essere un numero finito", {}
    if name == "stand":
        return True, "ok", {}
    if name == "walk":
        if "distance_m" not in args:
            return False, "walk: manca distance_m", {}
        speed = float(args.get("speed_mps", DEFAULT_WALK_SPEED))
        if speed == 0 or float(args["distance_m"]) == 0:
            return False, "walk: distance_m e speed_mps non possono essere 0", {}
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
    """Run one validated command on a driver (Go1Driver, MockDriver or SimDriver). Blocks until it is done.
    Returns the driver's WalkResult, or None for `stand`."""
    if name == "walk":
        vx = math.copysign(clean["speed_mps"], clean["distance_m"])
        return driver.walk(vx, 0.0, abs(clean["distance_m"]) / clean["speed_mps"])
    if name == "turn":
        vyaw = math.copysign(math.radians(clean["rate_dps"]), clean["degrees"])
        return driver.walk(0.0, vyaw, abs(clean["degrees"]) / clean["rate_dps"])
    if name == "stand":  # stay still for 1 s (keeps sending idle)
        t_end = driver.now() + 1.0
        while driver.now() < t_end and not driver.halt_event.is_set():
            driver.drive(0.0, 0.0)
            driver.sleep(0.02)
        return None
    prim = f"dance{int(clean['style'])}" if name == "dance" else PRIMITIVE_TOOLS[name]
    return driver.primitive(prim, clean.get("seconds"))
