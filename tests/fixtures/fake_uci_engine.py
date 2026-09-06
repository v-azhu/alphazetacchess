"""
A minimal fake UCI engine, speaking just enough of the protocol to
exercise `neural/pikafish_client.py`'s real subprocess communication
in `tests/test_pikafish_client_v062.py` without needing the actual
Pikafish binary present in this development environment.

Usage: `python3 fake_uci_engine.py <score_kind> <score_value> [mode]`
  e.g. `python3 fake_uci_engine.py cp 37`
       `python3 fake_uci_engine.py mate 5`
       `python3 fake_uci_engine.py cp 0 missing_network`  -- simulates
       Pikafish's real failure mode when it can't find its .nnue file:
       prints the same "ERROR: ... network file ... was not loaded"
       messages Pikafish itself prints, then exits without ever
       sending `bestmove`.

Always responds with a fixed, canned evaluation regardless of what
position it's asked about -- this fixture is for testing the CLIENT's
protocol handling, not for pretending to be a real engine. Echoes any
`setoption` command back as an `info string` line so tests can confirm
`PikafishClient` actually sent one (e.g. for `EvalFile`), since the
real UCI protocol doesn't otherwise acknowledge `setoption`.
"""

import sys


def main():
    score_kind, score_value = sys.argv[1], sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else None

    for line in sys.stdin:
        command = line.strip()

        if command == "uci":
            print("id name FakeEngine")
            print("uciok")
        elif command.startswith("setoption"):
            print(f"info string received: {command}")
        elif command == "isready":
            print("readyok")
        elif command.startswith("go"):
            if mode == "missing_network":
                print("info string ERROR: Network evaluation parameters compatible with the engine must be available.")
                print("info string ERROR: The network file pikafish.nnue was not loaded successfully.")
                print("info string ERROR: The engine will be terminated now.")
                sys.stdout.flush()
                return
            print(f"info depth 1 score {score_kind} {score_value} pv a0a1")
            print("bestmove a0a1")
        elif command == "quit":
            return
        # anything else: no reply needed.

        sys.stdout.flush()


if __name__ == "__main__":
    main()
