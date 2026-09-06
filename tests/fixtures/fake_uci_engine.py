"""
A minimal fake UCI engine, speaking just enough of the protocol to
exercise `neural/pikafish_client.py`'s real subprocess communication
in `tests/test_pikafish_client_v062.py` without needing the actual
Pikafish binary present in this development environment.

Usage: `python3 fake_uci_engine.py <score_kind> <score_value>`
  e.g. `python3 fake_uci_engine.py cp 37`
       `python3 fake_uci_engine.py mate 5`

Always responds with a fixed, canned evaluation regardless of what
position it's asked about -- this fixture is for testing the CLIENT's
protocol handling, not for pretending to be a real engine.
"""

import sys


def main():
    score_kind, score_value = sys.argv[1], sys.argv[2]

    for line in sys.stdin:
        command = line.strip()

        if command == "uci":
            print("id name FakeEngine")
            print("uciok")
        elif command == "isready":
            print("readyok")
        elif command.startswith("go"):
            print(f"info depth 1 score {score_kind} {score_value} pv a0a1")
            print("bestmove a0a1")
        elif command == "quit":
            return
        # "position fen ..." and anything else: no reply needed.

        sys.stdout.flush()


if __name__ == "__main__":
    main()
