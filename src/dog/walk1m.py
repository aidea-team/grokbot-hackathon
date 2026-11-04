"""Hello world: walk the Go1 forward ~1 m, then stand still.

    python src/dog/walk1m.py                 # mock (default, no dog needed)
    mjpython src/dog/walk1m.py --sim         # MuJoCo viewer (macOS needs mjpython)
    python src/dog/walk1m.py --real          # real dog: asks for confirmation first

Kill switch: press ENTER (or Ctrl+C) at any time -> zero velocity, dog stands still.
Keep the physical remote in hand anyway.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

from driver import MAX_VX, MAX_WALK_S, Go1Driver, JsonlLog, MockDriver


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--real", action="store_true", help="talk to the real dog (default: mock)")
    p.add_argument("--sim", action="store_true",
                   help="show the dog in the MuJoCo viewer (macOS: run with mjpython)")
    p.add_argument("--distance", type=float, default=1.0, help="meters (default 1.0)")
    p.add_argument("--speed", type=float, default=0.2, help=f"m/s, max {MAX_VX} (default 0.2)")
    args = p.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    log = JsonlLog()
    if args.real and args.sim:
        p.error("--real and --sim are mutually exclusive")
    if args.sim:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sim"))
        from go1_sim import SimDriver
        driver = SimDriver(log)
    else:
        driver = Go1Driver(log) if args.real else MockDriver(log)

    if args.real:
        print("REAL DOG. Checklist: dog standing, >= 2 m clear in front, remote in hand.")
        if input("Type 'go' to arm: ").strip().lower() != "go":
            print("aborted")
            return 1

    info = driver.connect()
    print(f"connected [{driver.name}]: {info}")

    # Local kill switch, independent of anything else: ENTER stops the dog.
    def kill_switch() -> None:
        try:
            sys.stdin.readline()
        except Exception:
            return
        if not done.is_set():
            log.event("kill_switch", source="keyboard")
            print("KILL SWITCH -> stopping")
            driver.halt()

    done = threading.Event()
    if sys.stdin.isatty():
        threading.Thread(target=kill_switch, daemon=True).start()
        print("press ENTER to stop")

    seconds = args.distance / args.speed if args.speed else 0
    print(f"walking {args.distance} m at {args.speed} m/s ({seconds:.1f} s)...")
    t0 = time.monotonic()
    try:
        # The validator caps a single command at MAX_WALK_S: chain commands for long distances.
        res, remaining = None, seconds
        while remaining > 1e-6:
            res = driver.walk(args.speed, 0.0, min(remaining, MAX_WALK_S))
            if not res.ok:
                break
            remaining -= MAX_WALK_S
    except KeyboardInterrupt:
        driver.halt()
        driver.stop()
        res = None
        print("Ctrl+C -> stopped")
    finally:
        done.set()
        driver.close()

    print(f"result: {res}  wall={time.monotonic() - t0:.2f}s  log={log.path}")
    if isinstance(driver, MockDriver):
        print(f"mock pose: {driver.pose()}")
    return 0 if res and res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
