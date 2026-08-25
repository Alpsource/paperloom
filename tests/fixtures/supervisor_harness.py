"""Standalone script run as a real subprocess by test_supervisor.py, playing
the role of "the parent process" that gets killed — the pytest process can't
SIGTERM itself, so these tests spawn this harness, kill *it*, and check what
happened to the children it spawned via paperloom.supervisor.spawn().

Usage: python supervisor_harness.py <mode> --out <path> [--gc-out <path>]

Modes:
  simple  spawn one long-running child, write its pid to --out, block.
  chain   spawn one child that itself forks a grandchild via a plain
          background shell job (not through paperloom's supervisor) —
          simulates e.g. MinerU spawning its own workers. Writes both pids
          to --out, blocks.
  many    spawn 10 children, write all 10 pids to --out, then os._exit(1)
          immediately (bypasses atexit) to simulate a hard crash.
"""

import argparse
import json
import os
import sys
import time

from paperloom.supervisor import spawn


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["simple", "chain", "many"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.mode == "simple":
        proc = spawn(["sleep", "100"])
        with open(args.out, "w") as f:
            json.dump({"child": proc.pid}, f)
        time.sleep(100)

    elif args.mode == "chain":
        gc_file = args.out + ".gc"
        proc = spawn(["bash", "-c", f"sleep 100 & echo $! > {gc_file}; wait"])
        # Wait for the grandchild's pid file to appear before reporting back.
        for _ in range(100):
            if os.path.exists(gc_file) and os.path.getsize(gc_file) > 0:
                break
            time.sleep(0.1)
        grandchild_pid = int(open(gc_file).read().strip())
        with open(args.out, "w") as f:
            json.dump({"child": proc.pid, "grandchild": grandchild_pid}, f)
        time.sleep(100)

    elif args.mode == "many":
        pids = [spawn(["sleep", "100"]).pid for _ in range(10)]
        with open(args.out, "w") as f:
            json.dump({"children": pids}, f)
        # Brief pause so the test can observe "alive" before the hard-exit —
        # PR_SET_PDEATHSIG kills children almost instantly after os._exit,
        # otherwise there'd be no window to check pre-death liveness.
        time.sleep(1)
        os._exit(1)


if __name__ == "__main__":
    sys.exit(main())
