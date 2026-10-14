"""Unified paired-match runner (V0.11.1).

The CLI deliberately keeps engine construction and match orchestration here. Python
SearchEngine instances run in-process; external engines use one line-oriented UCI/UCCI
adapter. Every game is replay-validated before it is appended to the JSONL evidence file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen, board_to_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.selfplay.paired_openings import select_paired_openings
from alphazetacchess.selfplay.sprt import GATES, PentanomialSPRT
from alphazetacchess.selfplay.recorder import load_records


def canonical_hash(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def machine_info():
    info = {
        "machine": platform.node() or "unknown",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "logical_cores": os.cpu_count() or 1,
        "physical_cores": None,
        "affinity": "none",
    }
    try:
        import psutil  # optional dependency
        info["physical_cores"] = psutil.cpu_count(logical=False)
    except ImportError:
        pass
    if info["physical_cores"] is None:
        # Conservative fallback when physical-core discovery is unavailable.
        info["physical_cores"] = info["logical_cores"]
    return info


def apply_affinity(worker_index=0):
    """Pin the current process to one allowed CPU when the platform supports it."""
    try:
        if hasattr(os, "sched_getaffinity") and hasattr(os, "sched_setaffinity"):
            allowed = sorted(os.sched_getaffinity(0))
            if allowed:
                os.sched_setaffinity(0, {allowed[worker_index % len(allowed)]})
                return sorted(os.sched_getaffinity(0))
        try:
            import psutil
            process = psutil.Process()
            allowed = process.cpu_affinity()
            if allowed:
                process.cpu_affinity([allowed[worker_index % len(allowed)]])
                return process.cpu_affinity()
        except (ImportError, AttributeError, OSError):
            pass
    except (AttributeError, OSError):
        pass
    return "none"


def system_load():
    try:
        import psutil
        return {"cpu_percent": psutil.cpu_percent(interval=None), "load_average": None}
    except ImportError:
        try:
            return {"cpu_percent": None, "load_average": list(os.getloadavg())}
        except (AttributeError, OSError):
            return {"cpu_percent": None, "load_average": None}


def load_openings(path, count, plies, seed):
    """Load paired openings in the agreed {initial_fen, opening_prefix} format."""
    if path:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        records = raw.get("openings", raw) if isinstance(raw, dict) else raw
        if not isinstance(records, list):
            raise ValueError("opening file must be a list or an object with an 'openings' list")
        openings = []
        seen = set()
        for item in records:
            if not isinstance(item, dict) or not item.get("initial_fen") or "opening_prefix" not in item:
                raise ValueError("each opening needs initial_fen and opening_prefix")
            board = board_from_fen(item["initial_fen"])
            if board.current_player != Color.RED:
                raise ValueError("paired opening position must have Red to move")
            key = " ".join(item["initial_fen"].split()[:2])
            if key in seen:
                continue
            seen.add(key)
            openings.append({
                "initial_fen": item["initial_fen"],
                "opening_prefix": item["opening_prefix"],
            })
        if len(openings) < count:
            raise ValueError(f"opening file has {len(openings)} distinct positions; need {count}")
        selected = random.Random(seed).sample(openings, count)
    else:
        source = ROOT / "data" / "selfplay.jsonl"
        if not source.exists():
            source = ROOT / "data" / "external_games.jsonl"
        if not source.exists():
            raise FileNotFoundError("provide --openings or a usable data/selfplay.jsonl source")
        selected = select_paired_openings(load_records(source), count, plies, seed)
    for index, item in enumerate(selected):
        item["opening_index"] = index
    return selected


class PythonEngine:
    def __init__(self, depth=5, movetime_ms=None, config=None):
        self.config = {"kind": "python", "depth": depth, **(config or {})}
        self.engine = SearchEngine(depth=depth, **(config or {}))
        self.movetime_ms = movetime_ms
        self.stats = []

    def choose_move(self, board, color, limit, initial_fen=None, moves=None):
        stop_event = threading.Event()
        timer = None
        if limit["kind"] == "movetime":
            timer = threading.Timer(limit["value"] / 1000.0, stop_event.set)
            timer.daemon = True
            timer.start()
        started = time.monotonic()
        try:
            if limit["kind"] == "depth":
                self.engine.depth = int(limit["value"])
            elif limit["kind"] == "nodes":
                raise ValueError("node limits apply to process engines only")
            result = self.engine.choose_move(board, color, stop_event=stop_event)
            self.stats.append({
                "depth": getattr(result, "depth", None),
                "nodes": getattr(result, "nodes_evaluated", None),
                "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            })
            if result.best_move is None:
                raise RuntimeError("Python engine returned no move")
            return result.best_move
        finally:
            if timer:
                timer.cancel()


class ProcessEngine:
    """Minimal persistent UCI/UCCI process adapter for fixed search limits."""
    def __init__(self, command, protocol="uci", timeout=60):
        if protocol not in {"uci", "ucci"}:
            raise ValueError("protocol must be uci or ucci")
        if not command:
            raise ValueError("process engine command is required")
        self.command = command
        self.protocol = protocol
        self.timeout = timeout
        self.config = {"kind": "process", "command": command, "protocol": protocol}
        self.stats = []
        self.process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
        self._send(protocol)
        self._read_until("uciok" if protocol == "uci" else "ucciok")
        self._send("isready")
        self._read_until("readyok")

    def _send(self, line):
        if self.process.poll() is not None:
            raise RuntimeError(f"engine process exited with code {self.process.returncode}")
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def _read_until(self, prefix):
        deadline = time.monotonic() + self.timeout
        lines = []
        while time.monotonic() < deadline:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError(f"engine exited before {prefix!r}; saw {lines[-8:]}")
            line = line.strip()
            lines.append(line)
            if line.startswith(prefix):
                return lines
        raise TimeoutError(f"engine timed out waiting for {prefix!r}")

    def choose_move(self, board, color, limit, initial_fen=None, moves=None):
        if limit["kind"] == "nodes" and self.protocol != "uci":
            raise ValueError("UCCI node limits are not supported by the current UCCI protocol")
        fen = initial_fen or board_to_fen(board)
        move_text = " ".join(moves or [])
        suffix = f" moves {move_text}" if move_text else ""
        self._send(f"position fen {fen}{suffix}")
        command = {"movetime": "movetime", "depth": "depth", "nodes": "nodes"}[limit["kind"]]
        self._send(f"go {command} {int(limit['value'])}")
        started = time.monotonic()
        lines = self._read_until("bestmove")
        fields = lines[-1].split()
        if len(fields) < 2 or fields[1] in {"(none)", "0000"}:
            raise RuntimeError(f"engine did not return a move: {lines[-1]}")
        move = GameRecord.move_from_iccs(fields[1])
        self.stats.append({
            "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
            "protocol": self.protocol,
            "limit": limit,
        })
        return move

    def close(self):
        if self.process.poll() is None:
            try:
                self._send("quit")
                self.process.wait(timeout=2)
            except Exception:
                self.process.kill()
                self.process.wait()


def play_game(opening, red_engine, black_engine, limit, max_moves, game_id, variant_color):
    board = board_from_fen(opening["initial_fen"])
    initial_fen = opening["initial_fen"]
    moves = []
    move_notations = []
    started = time.monotonic()
    while len(moves) < max_moves:
        side = board.current_player
        if Rule.is_game_over(board, side):
            result = "BLACK_WINS" if side == Color.RED else "RED_WINS"
            break
        engine = red_engine if side == Color.RED else black_engine
        move = engine.choose_move(
            board, side, limit, initial_fen=initial_fen, moves=move_notations
        )
        if not Rule.is_legal_move(board, move, side):
            raise ValueError(f"engine returned illegal move at ply {len(moves)}: {move}")
        moves.append({
            "color": side.name,
            "from": list(move.from_pos),
            "to": list(move.to_pos),
        })
        move_notations.append(GameRecord.move_to_iccs(move))
        board.move(move.from_pos, move.to_pos)
    else:
        result = "DRAW" if not Rule.is_game_over(board, board.current_player) else (
            "BLACK_WINS" if board.current_player == Color.RED else "RED_WINS"
        )
    record = {
        "game_id": game_id,
        "opening_index": opening["opening_index"],
        "initial_fen": initial_fen,
        "opening_prefix": opening.get("opening_prefix", []),
        "variant_color": variant_color,
        "result": result,
        "total_moves": len(moves),
        "moves": moves,
        "red_config": red_engine.config,
        "black_config": black_engine.config,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    validate_game(record, max_moves)
    return record


def validate_game(record, max_moves):
    board = board_from_fen(record["initial_fen"])
    moves = record["moves"]
    if record.get("total_moves") != len(moves):
        raise ValueError("recorded move count does not match move list")
    for ply, raw in enumerate(moves, 1):
        if Rule.is_game_over(board, board.current_player):
            raise ValueError(f"game continued after terminal position at ply {ply}")
        if raw["color"] != board.current_player.name:
            raise ValueError(f"wrong side to move at ply {ply}")
        move = Move(tuple(raw["from"]), tuple(raw["to"]))
        if not Rule.is_legal_move(board, move, board.current_player):
            raise ValueError(f"illegal recorded move at ply {ply}")
        board.move(move.from_pos, move.to_pos)
    terminal = Rule.is_game_over(board, board.current_player)
    if len(moves) == max_moves and not terminal:
        if record["result"] != "DRAW":
            raise ValueError("non-terminal move-limit result must be DRAW")
    elif not terminal:
        raise ValueError("game ended before a terminal result or move limit")
    else:
        winner = "BLACK_WINS" if board.current_player == Color.RED else "RED_WINS"
        if record["result"] != winner:
            raise ValueError("recorded result disagrees with terminal position")


def candidate_score(result, candidate_color):
    if result == "DRAW":
        return 0.5
    return 1.0 if result == f"{candidate_color}_WINS" else 0.0


def run(args):
    gate = GATES[args.gate]
    if args.workers > machine_info()["physical_cores"]:
        raise ValueError(
            f"--workers {args.workers} exceeds detected physical cores "
            f"({machine_info()['physical_cores']})"
        )
    if args.workers != 1:
        raise ValueError("this initial runner serializes games; use --workers 1 until parallel workers land")
    if args.a_kind == "process" and not args.a_command:
        raise ValueError("--a-command is required when --a-kind process")
    if args.b_kind == "process" and not args.b_command:
        raise ValueError("--b-command is required when --b-kind process")
    if args.limit_kind == "nodes" and (args.a_kind == "python" or args.b_kind == "python"):
        raise ValueError("node limits are supported for process engines only")
    output = Path(args.output)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    registration_path = output.with_suffix(output.suffix + ".registration.json")
    if output.exists() or manifest_path.exists() or registration_path.exists():
        raise ValueError("refusing to overwrite an existing output, manifest, or registration")
    openings = load_openings(args.openings, args.opening_count, args.opening_plies, args.seed)
    configs = {
        "a": {"kind": args.a_kind, "command": args.a_command, "protocol": args.a_protocol, "depth": args.a_depth},
        "b": {"kind": args.b_kind, "command": args.b_command, "protocol": args.b_protocol, "depth": args.b_depth},
    }
    limit = {"kind": args.limit_kind, "value": args.limit_value}
    revision = args.revision or os.environ.get("GITHUB_SHA")
    if not revision:
        try:
            revision = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            revision = "unknown"
    registration = {
        "test_id": args.test_id,
        "git_revision": revision,
        "config_hashes": {
            "a": canonical_hash({"engine": configs["a"], "limit": limit}),
            "b": canonical_hash({"engine": configs["b"], "limit": limit}),
        },
        "opening_set_hash": canonical_hash(openings),
        "opening_count": len(openings),
        "seed": args.seed,
        "gate": args.gate,
        "created_at_unix": time.time(),
    }
    registration["registration_id"] = canonical_hash({
        "git_revision": registration["git_revision"],
        "config_hashes": registration["config_hashes"],
        "opening_set_hash": registration["opening_set_hash"],
        "gate": registration["gate"],
    })
    # Registration history is append-only: an identical inconclusive or rejected
    # test cannot be repeated under a new output filename without a code revision.
    registry_path = ROOT / "data" / "match_registrations.jsonl"
    prior = {}
    if registry_path.exists():
        for line in registry_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            prior[item.get("registration_id")] = item.get("status", "REGISTERED")
    previous_status = prior.get(registration["registration_id"])
    if previous_status in {"INCONCLUSIVE", "ACCEPT_H0"}:
        raise ValueError(
            "identical registration already ended "
            f"{previous_status}; change code revision before rerunning"
        )
    # Durable registration is written before any engine starts or game begins.
    registration_path.parent.mkdir(parents=True, exist_ok=True)
    registration_path.write_text(json.dumps(registration, indent=2) + "\n", encoding="utf-8")
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("a", encoding="utf-8") as registry:
        registry.write(json.dumps({**registration, "status": "REGISTERED"}) + "\n")
    if args.limit_kind == "nodes" and (
        (args.a_kind == "process" and args.a_protocol == "ucci")
        or (args.b_kind == "process" and args.b_protocol == "ucci")
    ):
        raise ValueError("node limits require UCI process engines; UCCI node limits are unsupported")
    if args.limit_kind == "movetime" and limit["value"] < 1:
        raise ValueError("movetime must be positive")
    if args.limit_kind == "depth" and limit["value"] < 1:
        raise ValueError("depth must be positive")
    if args.limit_kind == "nodes" and limit["value"] < 1:
        raise ValueError("nodes must be positive")

    engines = []
    try:
        def build(kind, command, protocol, depth):
            if kind == "python":
                engine = PythonEngine(depth=depth)
            else:
                engine = ProcessEngine(shlex.split(command, posix=(os.name != "nt")), protocol=protocol)
            engines.append(engine)
            return engine
        a = build(args.a_kind, args.a_command, args.a_protocol, args.a_depth)
        b = build(args.b_kind, args.b_command, args.b_protocol, args.b_depth)
        affinity = apply_affinity()
        machine = machine_info()
        # Calibrate Python reference NPS with a short, reproducible depth-2 search.
        calibration = {"nodes": None, "elapsed_seconds": None, "nps": None}
        try:
            from alphazetacchess.core.board import Board
            probe = SearchEngine(depth=2)
            started = time.monotonic()
            probe_result = probe.choose_move(Board(), Color.RED)
            elapsed = max(time.monotonic() - started, 1e-9)
            nodes = getattr(probe_result, "nodes_evaluated", 0)
            calibration = {"nodes": nodes, "elapsed_seconds": elapsed, "nps": nodes / elapsed}
        except Exception as exc:
            calibration = {"error": str(exc), "nps": None}
        sprt = PentanomialSPRT(
            gate.h0_elo, gate.h1_elo, max_games=gate.max_games,
            alpha=0.05, beta=0.05, draw_rate=args.draw_rate,
        )
        counts = {"candidate_wins": 0, "candidate_losses": 0, "draws": 0}
        with output.open("x", encoding="utf-8") as records_file:
            game_index = 0
            for opening in openings:
                if sprt.state.value != "CONTINUE":
                    break
                # Same opening twice, candidate switches colors.
                for candidate_color in ("RED", "BLACK"):
                    if sprt.state.value != "CONTINUE":
                        break
                    game_index += 1
                    red_engine, black_engine = (a, b) if candidate_color == "RED" else (b, a)
                    load_before = system_load()
                    record = play_game(
                        opening, red_engine, black_engine, limit, args.max_moves,
                        f"{args.test_id}-{game_index:06d}", candidate_color,
                    )
                    record["load"] = {"before": load_before, "after": system_load()}
                    record["affinity"] = affinity
                    records_file.write(json.dumps(record, separators=(",", ":")) + "\n")
                    records_file.flush()
                    value = candidate_score(record["result"], candidate_color)
                    if value == 1.0:
                        counts["candidate_wins"] += 1
                    elif value == 0.0:
                        counts["candidate_losses"] += 1
                    else:
                        counts["draws"] += 1
                    # A pair is complete only after both colors for this opening.
                    if candidate_color == "BLACK":
                        # Candidate played Red then Black for this opening.
                        pair_score = pair_scores[0] + value
                        sprt.update(pair_score)
                    else:
                        pair_scores = [value]
        if sprt.state.value == "CONTINUE":
            sprt.finish("configured opening set exhausted before a likelihood boundary")
        result = sprt.result()
        manifest = {
            "test_id": args.test_id, "registration": registration,
            "gate": gate.__dict__, "limit": limit, "seed": args.seed,
            "openings": openings, "engine_configs": configs,
            "engine_hashes": {
                "a": sha256_file(args.a_command.split()[0]) if args.a_kind == "process" and Path(args.a_command.split()[0]).is_file() else None,
                "b": sha256_file(args.b_command.split()[0]) if args.b_kind == "process" and Path(args.b_command.split()[0]).is_file() else None,
            },
            "machine": machine, "affinity": affinity, "nps_calibration": calibration,
            "counts": counts, "sprt": {
                "state": result.state.value, "llr": result.llr,
                "lower_bound": result.lower_bound, "upper_bound": result.upper_bound,
                "pairs": result.pairs, "games": result.games,
                "pair_counts": result.pair_counts, "reason": result.reason,
            },
            "records": str(output), "generated_at_unix": time.time(),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        with registry_path.open("a", encoding="utf-8") as registry:
            registry.write(json.dumps({
                "registration_id": registration["registration_id"],
                "status": result.state.value,
                "finished_at_unix": time.time(),
            }) + "\\n")
        print(json.dumps(manifest["sprt"], indent=2))
    finally:
        for engine in engines:
            if isinstance(engine, ProcessEngine):
                engine.close()


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-id", required=True)
    parser.add_argument("--gate", choices=sorted(GATES), default="G2")
    parser.add_argument("--revision", default=None)
    parser.add_argument("--openings", default=None, help="opening-suite JSON; defaults to local archive")
    parser.add_argument("--opening-count", type=int, default=100)
    parser.add_argument("--opening-plies", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20261013)
    parser.add_argument("--draw-rate", type=float, default=0.2)
    parser.add_argument("--max-moves", type=int, default=150)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit-kind", choices=["movetime", "depth", "nodes"], default="movetime")
    parser.add_argument("--limit-value", type=int, default=500)
    for side in ("a", "b"):
        parser.add_argument(f"--{side}-kind", choices=["python", "process"], default="python")
        parser.add_argument(f"--{side}-command", default=None)
        parser.add_argument(f"--{side}-protocol", choices=["uci", "ucci"], default="uci")
        parser.add_argument(f"--{side}-depth", type=int, default=5)
    return parser


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    try:
        run(arguments)
    except Exception as error:
        print(f"match runner error: {error}", file=sys.stderr)
        raise
