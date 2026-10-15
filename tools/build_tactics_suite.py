"""Build AZ-TAC-500 or its explicitly synthetic 20-position smoke fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen, board_to_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.core.move import Move
from alphazetacchess.core.piece import PieceType
from alphazetacchess.core.rule import Rule
from alphazetacchess.neural.pikafish_client import mate_score_to_cp


DEFAULT_INPUT = ROOT / "data" / "external_games.jsonl"
DEFAULT_OUTPUT = ROOT / "data" / "suites" / "az_tac_500.json"
DEFAULT_SMOKE_OUTPUT = ROOT / "data" / "suites" / "az_tac_500_smoke.json"
FORMAT = "alphazeta-az-tac-500-v1"
SMOKE_FORMAT = "alphazeta-az-tac-smoke-v1"
CATEGORY_SPLIT_TARGETS = {
    "mate_in_1_3": {"dev": 60, "test": 40},
    "win_material": {"dev": 90, "test": 60},
    "avoid_blunder": {"dev": 90, "test": 60},
    "only_move_defense": {"dev": 30, "test": 20},
    "endgame": {"dev": 30, "test": 20},
}
CATEGORY_ORDER = tuple(CATEGORY_SPLIT_TARGETS)
MATE_CP = 9000


def _move_parts(raw_move):
    if isinstance(raw_move, str):
        move = GameRecord.move_from_iccs(raw_move)
        return move.from_pos, move.to_pos
    return tuple(raw_move["from"]), tuple(raw_move["to"])


def _canonical_fen(fen):
    return " ".join(fen.split()[:2])


def _fen_hash(fen):
    return hashlib.sha256(fen.encode("utf-8")).hexdigest()


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_for_fen(fen):
    return "dev" if int(_fen_hash(fen)[:16], 16) % 5 < 3 else "test"


def positions_from_records(records, min_ply=10, max_ply=120):
    """Replay archived games and deduplicate legal-to-move positions by board."""
    if min_ply < 1 or max_ply < min_ply:
        raise ValueError("invalid ply range")
    positions = {}
    for game_index, record in enumerate(records, start=1):
        board = (
            board_from_fen(record["initial_fen"])
            if record.get("initial_fen") else Board()
        )
        base_ply = 0
        if record.get("initial_fen"):
            fields = record["initial_fen"].split()
            if len(fields) >= 6:
                base_ply = (int(fields[5]) - 1) * 2 + (fields[1] == "b")
        for move_index, raw_move in enumerate(record.get("moves", []), start=1):
            from_pos, to_pos = _move_parts(raw_move)
            piece = board.get(*from_pos)
            target = board.get(*to_pos)
            if (
                piece is None
                or piece.color != board.current_player
                or (target is not None and target.color == board.current_player)
            ):
                break
            board.move(from_pos, to_pos)
            ply = base_ply + move_index
            if min_ply <= ply <= max_ply:
                fen = board_to_fen(board)
                key = _canonical_fen(fen)
                if key not in positions:
                    legal_moves = Rule.generate_legal_moves(
                        board, board.current_player
                    )
                    if not legal_moves:
                        continue
                    positions[key] = {
                        "fen": fen,
                        "position_hash": _fen_hash(fen),
                        "source_game": game_index,
                        "ply": ply,
                    }
    return sorted(positions.values(), key=lambda position: position["position_hash"])


def legal_moves_for_position(position):
    board = board_from_fen(position["fen"])
    legal_moves = Rule.generate_legal_moves(board, board.current_player)
    return [GameRecord.move_to_iccs(move) for move in legal_moves]


class PikafishRootLabeler:
    """Label root moves with one local UCI process and MultiPV/searchmoves."""

    def __init__(
        self,
        engine_path,
        network_path=None,
        top_depth=25,
        rest_depth=2,
        top_moves=5,
        threads=1,
    ):
        if min(top_depth, rest_depth, top_moves, threads) < 1:
            raise ValueError("depths, top_moves, and threads must be positive")
        self.top_depth = top_depth
        self.rest_depth = rest_depth
        self.top_moves = top_moves
        self.threads = threads
        self.engine_path = engine_path
        self.network_path = network_path
        self._multipv = None
        command = (
            [str(part) for part in engine_path]
            if isinstance(engine_path, (list, tuple))
            else [str(engine_path)]
        )
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        try:
            self._send("uci")
            self.uci_lines = self._read_until("uciok")
            if threads > 1:
                self._send(f"setoption name Threads value {threads}")
            if network_path is not None:
                self._send(f"setoption name EvalFile value {network_path}")
            self._send("isready")
            self._read_until("readyok")
        except Exception:
            self.close()
            raise

    def _send(self, command):
        if self._process.poll() is not None:
            raise RuntimeError("Pikafish exited unexpectedly")
        self._process.stdin.write(command + "\n")
        self._process.stdin.flush()

    def _read_until(self, prefix):
        lines = []
        while True:
            line = self._process.stdout.readline()
            if not line:
                raise RuntimeError(
                    f"Pikafish exited before {prefix!r}; output: {lines[-10:]}"
                )
            line = line.strip()
            lines.append(line)
            if line.startswith(prefix):
                return lines

    def _set_multipv(self, value):
        if self._multipv == value:
            return
        self._send(f"setoption name MultiPV value {value}")
        self._send("isready")
        self._read_until("readyok")
        self._multipv = value

    @staticmethod
    def _score_from_info(tokens):
        index = tokens.index("score")
        kind = tokens[index + 1]
        value = int(tokens[index + 2])
        if kind == "cp":
            return value, None
        if kind == "mate":
            return mate_score_to_cp(value), value
        raise ValueError(f"unsupported UCI score type: {kind}")

    def _analyze(self, fen, depth, multipv, searchmoves=None):
        self._set_multipv(multipv)
        self._send(f"position fen {fen}")
        command = f"go depth {depth}"
        if searchmoves:
            command += f" searchmoves {' '.join(searchmoves)}"
        self._send(command)
        lines = self._read_until("bestmove")
        by_line = {}
        for line in lines:
            tokens = line.split()
            if not tokens or tokens[0] != "info" or "score" not in tokens:
                continue
            if "depth" not in tokens or "pv" not in tokens:
                continue
            line_depth = int(tokens[tokens.index("depth") + 1])
            line_multipv = (
                int(tokens[tokens.index("multipv") + 1])
                if "multipv" in tokens else 1
            )
            pv_index = tokens.index("pv")
            if pv_index + 1 >= len(tokens):
                continue
            score_cp, mate_in = self._score_from_info(tokens)
            parsed = {
                "move": tokens[pv_index + 1],
                "score_cp": score_cp,
                "mate_in": mate_in,
                "depth": line_depth,
            }
            if line_multipv not in by_line or line_depth >= by_line[line_multipv]["depth"]:
                by_line[line_multipv] = parsed
        return by_line

    def label_position(self, fen, legal_moves):
        legal_set = set(legal_moves)
        if not legal_set:
            raise ValueError(f"No legal root moves in {fen}")
        top_count = min(self.top_moves, len(legal_set))
        high_lines = self._analyze(fen, self.top_depth, top_count)
        high_scores = {}
        for line in high_lines.values():
            if line["depth"] < self.top_depth:
                continue
            if line["move"] not in legal_set:
                raise RuntimeError(f"Pikafish returned illegal move {line['move']!r}")
            high_scores[line["move"]] = line
        if len(high_scores) != top_count:
            raise RuntimeError(
                f"Pikafish returned {len(high_scores)} root moves at depth "
                f"{self.top_depth}; expected {top_count}"
            )

        scores = dict(high_scores)
        remaining_moves = [move for move in legal_moves if move not in scores]
        if remaining_moves:
            lower_lines = self._analyze(
                fen,
                self.rest_depth,
                len(remaining_moves),
                searchmoves=remaining_moves,
            )
            for line in lower_lines.values():
                if line["depth"] < self.rest_depth:
                    continue
                if line["move"] not in remaining_moves:
                    raise RuntimeError(
                        f"Pikafish returned unexpected forced-root move {line['move']!r}"
                    )
                scores[line["move"]] = line
            missing = set(remaining_moves) - set(scores)
            if missing:
                raise RuntimeError(
                    f"Pikafish did not complete depth {self.rest_depth} for "
                    f"{len(missing)} legal moves: {sorted(missing)[:5]}"
                )
        ranked_high = sorted(
            high_scores.values(),
            key=lambda score: (-score["score_cp"], score["move"]),
        )
        best_score = ranked_high[0]["score_cp"]
        return {
            "best_move": ranked_high[0]["move"],
            "best_score_cp": best_score,
            "top_moves": [score["move"] for score in ranked_high],
            "best_moves": [
                score["move"]
                for score in ranked_high
                if score["score_cp"] == best_score
            ],
            "scores": [
                {
                    **scores[move],
                    "source": "multipv" if move in high_scores else "forced-root",
                }
                for move in legal_moves
            ],
        }

    def close(self):
        process = getattr(self, "_process", None)
        if process is None:
            return
        if process.poll() is None:
            try:
                self._send("quit")
            except (BrokenPipeError, RuntimeError):
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        finally:
            if process.stdin is not None:
                process.stdin.close()
            if process.stdout is not None:
                process.stdout.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def provenance(self):
        engine_path = (
            self.engine_path[0]
            if isinstance(self.engine_path, (list, tuple))
            else self.engine_path
        )
        return {
            "engine": next(
                (line for line in self.uci_lines if line.startswith("id name ")),
                "Pikafish (UCI id unavailable)",
            ),
            "binary_name": Path(engine_path).name,
            "binary_sha256": _sha256_file(engine_path),
            "network_name": (
                Path(self.network_path).name if self.network_path else None
            ),
            "network_sha256": (
                _sha256_file(self.network_path) if self.network_path else None
            ),
            "top_depth": self.top_depth,
            "top_moves": self.top_moves,
            "other_move_depth": self.rest_depth,
            "threads": self.threads,
            "platform": platform.platform(),
        }


class FakeLabeler:
    """Deterministic synthetic labels for tests and the smoke-only fixture."""

    def label_position(self, fen, legal_moves):
        ordered = sorted(legal_moves)
        ranked = sorted(
            ordered,
            key=lambda move: hashlib.sha256(f"{fen}:{move}".encode()).hexdigest(),
        )
        scores = {
            move: {
                "move": move,
                "score_cp": 100 - index * 10,
                "mate_in": None,
                "depth": 25,
                "source": "synthetic-smoke",
            }
            for index, move in enumerate(ranked)
        }
        best_move = ranked[0]
        return {
            "best_move": best_move,
            "best_score_cp": scores[best_move]["score_cp"],
            "top_moves": ranked[:5],
            "best_moves": [best_move],
            "scores": [scores[move] for move in legal_moves],
        }


def _validate_labels(legal_moves, labels, required_top_depth=None):
    expected = set(legal_moves)
    scores = labels.get("scores", [])
    by_move = {score["move"]: score for score in scores}
    if len(by_move) != len(scores) or set(by_move) != expected:
        raise ValueError("labeler must score each legal move exactly once")
    for score in scores:
        if not isinstance(score.get("score_cp"), int) or score.get("depth", 0) < 1:
            raise ValueError(f"invalid score/depth for move {score.get('move')!r}")
    top_moves = labels.get("top_moves", [])
    if not top_moves or any(move not in expected for move in top_moves):
        raise ValueError("labeler returned missing or illegal high-depth moves")
    if required_top_depth is not None:
        for move in top_moves:
            if by_move[move]["depth"] < required_top_depth:
                raise ValueError(
                    f"top move {move} has depth {by_move[move]['depth']}, "
                    f"expected at least {required_top_depth}"
                )
    if labels.get("best_move") not in top_moves:
        raise ValueError("best_move must be one of the high-depth moves")
    best_move = labels["best_move"]
    if labels.get("best_score_cp") != by_move[best_move]["score_cp"]:
        raise ValueError("best_score_cp must match the best_move label")
    best_moves = labels.get("best_moves") or [best_move]
    if any(
        move not in top_moves or by_move[move]["score_cp"] != labels["best_score_cp"]
        for move in best_moves
    ):
        raise ValueError("best_moves must be depth-qualified moves tied for best score")
    return by_move


def _category_for(position, labels, remaining):
    by_move = _validate_labels(position["legal_moves"], labels)
    high_moves = labels["top_moves"]
    best_move = labels["best_move"]
    best_score = labels["best_score_cp"]
    first_five = position["legal_moves"][:5]
    non_king_count = sum(
        1
        for row in board_from_fen(position["fen"]).board
        for piece in row
        if piece is not None and piece.type != PieceType.KING
    )

    qualifies = {
        "mate_in_1_3": any(
            by_move[move].get("mate_in") is not None
            and 1 <= by_move[move]["mate_in"] <= 3
            for move in high_moves
        ),
        "only_move_defense": (
            best_score >= 0
            and all(
                score["score_cp"] <= best_score - 300
                for move, score in by_move.items()
                if move != best_move
            )
        ),
        "avoid_blunder": sum(
            by_move[move]["score_cp"] <= best_score - 300
            for move in first_five
        ) >= 3,
        "win_material": best_score >= 300,
        "endgame": non_king_count <= 8,
    }
    split = split_for_fen(position["fen"])
    for category in CATEGORY_ORDER:
        if qualifies[category] and remaining.get(category, {}).get(split, 0) > 0:
            return category, split
    return None, split


def _record_labeled_position(position, labels, category=None, split=None):
    _validate_labels(position["legal_moves"], labels)
    return {
        "position_hash": position["position_hash"],
        "fen": position["fen"],
        "source_game": position["source_game"],
        "ply": position["ply"],
        "split": split or split_for_fen(position["fen"]),
        "category": category,
        "legal_moves": position["legal_moves"],
        "best_move": labels["best_move"],
        "best_moves": labels.get("best_moves") or [labels["best_move"]],
        "best_score_cp": labels["best_score_cp"],
        "top_moves": labels["top_moves"],
        "move_scores": labels["scores"],
        "label_depth": min(
            next(score["depth"] for score in labels["scores"] if score["move"] == move)
            for move in labels["top_moves"]
        ),
    }


def build_tactics_suite(
    candidates,
    labeler,
    category_split_targets=None,
    max_candidates=None,
    required_top_depth=25,
    progress_callback=None,
):
    targets = category_split_targets or CATEGORY_SPLIT_TARGETS
    remaining = {
        category: dict(split_counts)
        for category, split_counts in targets.items()
    }
    ordered = sorted(candidates, key=lambda candidate: candidate["position_hash"])
    if max_candidates is not None:
        ordered = ordered[:max_candidates]
    suite_positions = []
    labeled_count = 0
    for position in ordered:
        if not any(any(counts.values()) for counts in remaining.values()):
            break
        position = dict(position)
        position["legal_moves"] = position.get("legal_moves") or legal_moves_for_position(position)
        labels = labeler.label_position(position["fen"], position["legal_moves"])
        _validate_labels(
            position["legal_moves"], labels, required_top_depth=required_top_depth
        )
        category, split = _category_for(position, labels, remaining)
        labeled_count += 1
        if progress_callback is not None and labeled_count % 50 == 0:
            progress_callback(labeled_count, len(suite_positions), len(ordered))
        if category is None:
            continue
        suite_positions.append(
            _record_labeled_position(position, labels, category, split)
        )
        remaining[category][split] -= 1

    if any(any(counts.values()) for counts in remaining.values()):
        raise RuntimeError(
            "Could not fill the fixed AZ-TAC category/split targets; "
            f"labeled {labeled_count} candidates, remaining={remaining}"
        )
    suite_positions.sort(key=lambda position: position["position_hash"])
    return {
        "format": FORMAT,
        "smoke_only": False,
        "label_provenance": "Pikafish; local engine and network are not included",
        "top_move_min_depth": required_top_depth,
        "category_split_targets": targets,
        "candidate_positions_labeled": labeled_count,
        "positions": suite_positions,
    }


def build_smoke_suite(
    candidates,
    count=20,
    labeler=None,
    required_top_depth=None,
    label_provenance=None,
):
    if count < 1:
        raise ValueError("smoke count must be positive")
    labeler = labeler or FakeLabeler()
    ordered = sorted(candidates, key=lambda candidate: candidate["position_hash"])
    if len(ordered) < count:
        raise ValueError(f"need {count} smoke positions, found {len(ordered)}")
    positions = []
    for source_position in ordered[:count]:
        candidate = dict(source_position)
        candidate["legal_moves"] = (
            candidate.get("legal_moves") or legal_moves_for_position(candidate)
        )
        labels = labeler.label_position(candidate["fen"], candidate["legal_moves"])
        _validate_labels(
            candidate["legal_moves"], labels, required_top_depth=required_top_depth
        )
        positions.append(
            _record_labeled_position(candidate, labels, "synthetic_smoke")
        )
    return {
        "format": SMOKE_FORMAT,
        "smoke_only": True,
        "label_provenance": label_provenance or (
            "synthetic deterministic fixture; not game-strength evidence"
        ),
        "positions": positions,
    }


def read_records(path):
    with Path(path).open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}:{line_number}") from exc


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target:
        json.dump(data, target, separators=(",", ":"), ensure_ascii=False)
        target.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pikafish-path", type=Path)
    parser.add_argument("--network-path", type=Path)
    parser.add_argument("--top-depth", type=int, default=25)
    parser.add_argument("--rest-depth", type=int, default=2)
    parser.add_argument("--top-moves", type=int, default=5)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--max-candidates", type=int)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--label-smoke", action="store_true")
    parser.add_argument("--smoke-count", type=int, default=20)
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error(f"input file does not exist: {args.input}")
    if args.network_path and not args.pikafish_path:
        parser.error("--network-path requires --pikafish-path")
    if args.threads < 1:
        parser.error("--threads must be positive")
    if args.smoke and args.label_smoke:
        parser.error("--smoke and --label-smoke are mutually exclusive")
    if not args.smoke and not args.pikafish_path:
        parser.error("AZ-TAC-500 labeling requires --pikafish-path; use --smoke for tests")

    candidates = positions_from_records(read_records(args.input))
    output = args.output or (
        ROOT / "data" / "suites" / "az_tac_20_pikafish_smoke.json"
        if args.label_smoke
        else DEFAULT_SMOKE_OUTPUT if args.smoke else DEFAULT_OUTPUT
    )
    if args.smoke:
        suite = build_smoke_suite(candidates, args.smoke_count)
    elif args.label_smoke:
        with PikafishRootLabeler(
            args.pikafish_path,
            args.network_path,
            top_depth=args.top_depth,
            rest_depth=args.rest_depth,
            top_moves=args.top_moves,
            threads=args.threads,
        ) as labeler:
            suite = build_smoke_suite(
                candidates,
                args.smoke_count,
                labeler=labeler,
                required_top_depth=args.top_depth,
                label_provenance=(
                    "Pikafish; real labels for smoke validation only, not the 500-position suite"
                ),
            )
            suite["labeler"] = labeler.provenance()
        suite["top_move_min_depth"] = args.top_depth
        suite["other_move_max_depth"] = args.rest_depth
        suite["threads"] = args.threads
    else:
        started = time.monotonic()
        with PikafishRootLabeler(
            args.pikafish_path,
            args.network_path,
            top_depth=args.top_depth,
            rest_depth=args.rest_depth,
            top_moves=args.top_moves,
            threads=args.threads,
        ) as labeler:
            suite = build_tactics_suite(
                candidates,
                labeler,
                max_candidates=args.max_candidates,
                required_top_depth=args.top_depth,
                progress_callback=lambda labeled, selected, total: print(
                    f"Labeled {labeled}/{total} candidates; selected {selected}/500",
                    flush=True,
                ),
            )
            suite["labeler"] = labeler.provenance()
        suite["labeling_elapsed_seconds"] = round(time.monotonic() - started, 3)
        suite["other_move_max_depth"] = args.rest_depth
        suite["threads"] = args.threads
        suite["deviations"] = [
            "Only the MultiPV top moves are labeled at the requested top depth; "
            "remaining legal moves use forced-root searches at the configured lower depth."
        ]
    suite["source_archive"] = str(args.input.relative_to(ROOT)) \
        if args.input.is_relative_to(ROOT) else str(args.input)
    write_json(output, suite)
    print(f"Wrote {len(suite['positions'])} positions to {output}")


if __name__ == "__main__":
    main()
