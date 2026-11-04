#!/usr/bin/env python3
"""A short, bounded walk of the real G1: LocoClient.Move for a few seconds, then StopMove. Never changes the FSM mode.

    .venv/bin/python scripts/g1_walk.py --vx 0.2 --seconds 2 [--vy 0] [--vyaw 0] [--iface en0]

Limits (hard): |vx| <= 0.3 m/s, |vy| <= 0.2 m/s, |vyaw| <= 0.4 rad/s, <= 3 s. StopMove is always sent at the end (also on Ctrl+C or error).
Operator: remote in hand. Emergency stop = damp on the remote, or `scripts/g1_fsm.py set 1`. Logs to logs/g1-walk.jsonl.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

LOG = Path(__file__).resolve().parents[1] / "logs" / "g1-walk.jsonl"


def log(event: str, **f) -> None:
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(json.dumps({"ts": round(time.time(), 3), "event": event, **f}) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vx", type=float, default=0.2)
    ap.add_argument("--vy", type=float, default=0.0)
    ap.add_argument("--vyaw", type=float, default=0.0)
    ap.add_argument("--seconds", type=float, default=2.0)
    ap.add_argument("--iface", default="en0")
    a = ap.parse_args()
    if abs(a.vx) > 0.3 or abs(a.vy) > 0.2 or abs(a.vyaw) > 0.4 or not (0.2 <= a.seconds <= 3.0):
        print("RIFIUTATO: fuori dai limiti (|vx|<=0.3, |vy|<=0.2, |vyaw|<=0.4, 0.2<=secondi<=3)")
        return 2

    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

    ChannelFactoryInitialize(0, a.iface)
    loco = LocoClient()
    loco.SetTimeout(3.0)
    loco.Init()
    code, fsm = loco.GetFsmId()
    print(f"FSM prima: {fsm if code == 0 else 'ERRORE ' + str(code)}")
    if code != 0:
        print("RIFIUTATO: non leggo lo stato del robot")
        return 2
    log("walk_start", vx=a.vx, vy=a.vy, vyaw=a.vyaw, seconds=a.seconds, fsm=fsm)
    codes: list[int] = []
    try:
        t0 = time.monotonic()
        while time.monotonic() - t0 < a.seconds:
            codes.append(loco.Move(a.vx, a.vy, a.vyaw))
            time.sleep(0.1)
    finally:
        stop = loco.StopMove()
        print(f"StopMove inviato: {stop}")
    time.sleep(0.5)
    code2, fsm2 = loco.GetFsmId()
    print(f"Move inviato {len(codes)} volte, codici: {sorted(set(codes))}; FSM dopo: {fsm2 if code2 == 0 else 'ERRORE ' + str(code2)}")
    log("walk_end", move_codes=sorted(set(codes)), stop=stop, fsm_after=fsm2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
