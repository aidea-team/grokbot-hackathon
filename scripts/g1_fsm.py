#!/usr/bin/env python3
"""Read or change the G1's FSM mode (high-level, via LocoClient on the robot's own `sport` service). Logs to logs/g1-fsm.jsonl.

    .venv/bin/python scripts/g1_fsm.py read                 # read only: FSM id + control mode
    .venv/bin/python scripts/g1_fsm.py set 500 [--iface en0]  # Start (locked stand per third-party sources)
    .venv/bin/python scripts/g1_fsm.py set 501                # walking (Regular mode on the 29 DoF / 3-DoF waist G1, same sources)
    .venv/bin/python scripts/g1_fsm.py set 1                  # DAMP: the quick "stop" (motors limp, the robot sags): keep the remote too

Only ids 1, 500 and 501 are accepted: no zero-torque, sit, squat or lie-down transitions, no developer mode, no low level.
After the request it waits and reads the FSM back, and says plainly whether the robot changed. Needs the SDK (cyclonedds 0.10.2).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ALLOWED = {1: "Damp", 500: "Start (SDK LocoClient.Start)", 501: "walking mode (third-party sources, VERIFY)"}
LOG = Path(__file__).resolve().parents[1] / "logs" / "g1-fsm.jsonl"


def log(event: str, **f) -> None:
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(json.dumps({"ts": round(time.time(), 3), "event": event, **f}) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["read", "set"])
    ap.add_argument("fsm_id", type=int, nargs="?")
    ap.add_argument("--iface", default="en0")
    ap.add_argument("--wait", type=float, default=2.0, help="seconds to wait before reading back")
    args = ap.parse_args()

    from unitree_sdk2py.comm.motion_switcher.motion_switcher_client import MotionSwitcherClient
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

    ChannelFactoryInitialize(0, args.iface)
    loco = LocoClient()
    loco.SetTimeout(5.0)
    loco.Init()
    msw = MotionSwitcherClient()
    msw.SetTimeout(5.0)
    msw.Init()

    def read() -> tuple[int | None, object]:
        code, fsm = loco.GetFsmId()
        mcode, mode = msw.CheckMode()
        print(f"  FSM id: {fsm if code == 0 else 'ERRORE ' + str(code)}   control mode: {mode if mcode == 0 else 'ERRORE ' + str(mcode)}")
        return (fsm if code == 0 else None), mode

    print("stato attuale:")
    before, mode = read()
    log("read", fsm=before, mode=mode)
    if args.action == "read":
        return 0

    if args.fsm_id not in ALLOWED:
        print(f"RIFIUTATO: accetto solo {sorted(ALLOWED)} ({ALLOWED})")
        return 2
    if isinstance(mode, dict) and mode.get("name") not in ("ai", "normal", None):
        print(f"RIFIUTATO: il robot non è in una modalità interna normale ({mode}): developer mode?")
        return 2
    print(f"invio SetFsmId({args.fsm_id}) = {ALLOWED[args.fsm_id]}")
    log("set_fsm_id_request", fsm_id=args.fsm_id, before=before)
    code = loco.SetFsmId(args.fsm_id)
    print(f"  risposta: {code}")
    time.sleep(args.wait)
    print("stato dopo:")
    after, _ = read()
    log("set_fsm_id_result", fsm_id=args.fsm_id, code=code, after=after)
    if after == args.fsm_id:
        print(f"RIUSCITO: il robot è in FSM {after}")
        return 0
    print(f"NON CAMBIATO: richiesta accettata (codice {code}) ma l'FSM è ancora {after}, non {args.fsm_id}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
