"""Paths to the MuJoCo models we use (from mujoco_menagerie, cloned in vendor/ by scripts/setup.sh)."""
from pathlib import Path

MENAGERIE = Path(__file__).resolve().parents[2] / "vendor" / "mujoco_menagerie"

MODELS = {
    "go1": MENAGERIE / "unitree_go1" / "scene.xml",
    "ur5e": MENAGERIE / "universal_robots_ur5e" / "scene.xml",
}


def model_path(name: str) -> Path:
    try:
        path = MODELS[name]
    except KeyError:
        raise SystemExit(f"unknown model {name!r}, choose from {sorted(MODELS)}")
    if not path.exists():
        raise SystemExit(f"{path} not found: run ./scripts/setup.sh")
    return path
