"""V0.6.2 minimal UCI client, for talking to an external engine
(Pikafish, in particular) as a position-evaluation oracle.

Deliberately minimal -- this only implements the handful of UCI
commands needed to ask "what do you think of this position": `uci`/
`uciok`, `isready`/`readyok`, `position fen ...`, and `go movetime
...` followed by reading `info ...` lines until `bestmove ...`. It is
NOT a general UCI GUI backend (no pondering, no multi-PV, no time
management beyond a fixed per-position `movetime`).

## Why this is tested against a FAKE engine, not the real Pikafish

This project's own test suite can't depend on a real Pikafish binary
being present (it isn't, and the whole reason this module exists is
that the *user's* machine has one, not this development environment's
sandbox -- see `docs/v0.6.2.md`). `tests/test_pikafish_client_v062.py`
launches a tiny, self-contained fake UCI engine (a short Python script
that speaks just enough of the protocol to be useful) as a real
subprocess, so `PikafishClient`'s actual stdin/stdout plumbing and
`info` line parsing get exercised end to end -- not mocked out -- while
still not requiring Pikafish itself to run this project's test suite.
Whether the real Pikafish binary is actually reachable and behaves the
same way is confirmed separately, once, in `docs/v0.6.2.md`'s smoke
test on the user's own machine.
"""

import subprocess


class PikafishClient:
    """
    A running external UCI engine process, kept alive across multiple
    `evaluate_fen` calls (starting a fresh process per position would
    make labeling thousands of positions far slower than necessary --
    NNUE engines' own startup cost, loading the network file, is not
    negligible).
    """

    def __init__(self, engine_path, movetime_ms=200, network_path=None):
        self.movetime_ms = movetime_ms
        self._process = subprocess.Popen(
            engine_path if isinstance(engine_path, list) else [engine_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,  # line-buffered
        )
        self._send("uci")
        self._read_until("uciok")
        if network_path is not None:
            # Pikafish (and NNUE engines generally) can't search at
            # all without a network loaded -- if it isn't sitting next
            # to the executable under its default expected name/path,
            # this must be set explicitly before `isready`/`go`, or
            # every `go` command will fail with an "ERROR: The network
            # file ... was not loaded successfully" message and the
            # process will exit instead of ever sending `bestmove`.
            self._send(f"setoption name EvalFile value {network_path}")
        self._send("isready")
        # Stored (not just discarded) so tests can confirm a setoption
        # command was actually sent and acknowledged, not just that
        # the handshake didn't hang.
        self.handshake_lines = self._read_until("readyok")

    def _send(self, command):
        self._process.stdin.write(command + "\n")
        self._process.stdin.flush()

    def _read_until(self, sentinel_prefix):
        """Read and return lines until one starts with `sentinel_prefix`."""
        lines = []
        while True:
            line = self._process.stdout.readline()
            if line == "":
                hint = ""
                if any("EvalFile" in seen or "network file" in seen for seen in lines):
                    hint = (
                        "\n\nThis looks like Pikafish couldn't find its .nnue network "
                        "file. Pass --network-path pointing at pikafish.nnue (download "
                        "from https://github.com/official-pikafish/Networks/releases "
                        "if you don't have it), or place it next to the executable "
                        "under its default expected name."
                    )
                raise RuntimeError(
                    f"Engine process exited before sending a line starting "
                    f"with {sentinel_prefix!r}. Lines seen: {lines}{hint}"
                )
            line = line.strip()
            lines.append(line)
            if line.startswith(sentinel_prefix):
                return lines

    def evaluate_fen(self, fen):
        """
        Ask the engine to evaluate `fen` for `self.movetime_ms`
        milliseconds. Returns a dict:
            {"score_cp": <int, from the side-to-move's perspective, or
                          None if the engine only ever reported a mate
                          score>,
             "mate_in": <int, plies to mate, signed (positive = the
                         side to move delivers it), or None>,
             "best_move": <str, engine's UCI move notation>}

        Per the UCI protocol, `score cp` is always from the
        perspective of whichever side is to move in the FEN sent --
        exactly matching this project's own `evaluate()` convention of
        scoring from `perspective_color`'s point of view, so no sign
        flip is needed when using this as a training label for a
        position encoded via `neural/features.py`'s `color`-relative
        scheme.
        """
        self._send(f"position fen {fen}")
        self._send(f"go movetime {self.movetime_ms}")
        lines = self._read_until("bestmove")

        score_cp = None
        mate_in = None
        for line in lines:
            if not line.startswith("info "):
                continue
            tokens = line.split()
            if "score" not in tokens:
                continue
            score_index = tokens.index("score")
            kind = tokens[score_index + 1]
            value = int(tokens[score_index + 2])
            if kind == "cp":
                score_cp = value
                mate_in = None
            elif kind == "mate":
                mate_in = value
                score_cp = None

        best_move = lines[-1].split()[1] if len(lines[-1].split()) > 1 else None

        return {"score_cp": score_cp, "mate_in": mate_in, "best_move": best_move}

    def close(self):
        try:
            self._send("quit")
            self._process.wait(timeout=5)
        except Exception:
            self._process.kill()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def mate_score_to_cp(mate_in, saturation=9000, decay_per_ply=10):
    """
    Convert a UCI `score mate N` into a single comparable centipawn-
    like number for training purposes: a large, saturating value whose
    sign matches who's winning and whose magnitude decreases slightly
    with distance to mate (a mate-in-1 is a "more certain" evaluation
    than a mate-in-30, even though both are technically won). Positive
    `mate_in` means the side to move delivers mate; negative means
    they get mated.
    """
    sign = 1 if mate_in > 0 else -1
    plies = abs(mate_in)
    return sign * max(saturation - decay_per_ply * plies, 0)
