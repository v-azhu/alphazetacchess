import random
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_to_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.core.move import Move
from alphazetacchess.core.rule import Rule
from tools.build_opening_suite import build_openings, material_balance_cp
from tools.build_tactics_suite import (
    FakeLabeler,
    PikafishRootLabeler,
    build_smoke_suite,
    build_tactics_suite,
    positions_from_records,
    split_for_fen,
)
from tools.eval_tactics import evaluate_suite
from tools.extract_fallback_positions import extract_fallback_positions


def _game(seed, plies=16):
    rng = random.Random(seed)
    board = Board()
    moves = []
    for _ in range(plies):
        move = rng.choice(Rule.generate_legal_moves(board, board.current_player))
        moves.append({"from": list(move.from_pos), "to": list(move.to_pos)})
        board.move(move.from_pos, move.to_pos)
    return {"moves": moves}


class _HighMaterialFakeLabeler:
    def label_position(self, fen, legal_moves):
        ranked = list(legal_moves)
        scores = [
            {
                "move": move,
                "score_cp": 500 - index,
                "mate_in": None,
                "depth": 25,
                "source": "fake-test",
            }
            for index, move in enumerate(ranked)
        ]
        return {
            "best_move": ranked[0],
            "best_moves": [ranked[0]],
            "best_score_cp": scores[0]["score_cp"],
            "top_moves": ranked[:5],
            "scores": scores,
        }


def test_opening_suite_is_distinct_replayable_and_material_balanced():
    records = [_game(seed, plies=10) for seed in range(12)]
    suite, counts = build_openings(records, opening_count=8, seed=91)

    assert len(suite) == 8
    assert len({tuple(opening["initial_fen"].split()[:2]) for opening in suite}) == 8
    assert counts["balanced_openings"] >= 8
    for opening in suite:
        assert opening["initial_fen"].split()[1] == "w"
        assert len(opening["opening_prefix"]) == 8
        board = Board()
        for raw_move in opening["opening_prefix"]:
            assert raw_move["color"] == board.current_player.name
            from_pos = tuple(raw_move["from"])
            to_pos = tuple(raw_move["to"])
            assert Rule.is_legal_move(board, Move(from_pos, to_pos), board.current_player)
            board.move(from_pos, to_pos)
        assert board_to_fen(board) == opening["initial_fen"]
        assert abs(material_balance_cp(board)) <= 100


def test_opening_suite_rejects_insufficient_balanced_positions():
    with pytest.raises(ValueError, match="Need 2 balanced distinct openings"):
        build_openings([_game(1, plies=8)], opening_count=2)


def test_fallback_extractor_maps_depth_zero_to_alpha_position():
    board = Board()
    moves = []
    for _ in range(4):
        move = Rule.generate_legal_moves(board, board.current_player)[0]
        moves.append({
            "color": board.current_player.name,
            "from": list(move.from_pos),
            "to": list(move.to_pos),
        })
        board.move(move.from_pos, move.to_pos)
    record = {
        "initial_fen": board_to_fen(Board()),
        "pikafish_color": "BLACK",
        "opening_index": 4,
        "moves": moves,
        "search_stats": {
            "alphazeta": [
                {"side": "RED", "depth": 0, "elapsed_ms": 501.2},
                {"side": "RED", "depth": 2, "elapsed_ms": 499.1},
            ]
        },
    }

    positions = extract_fallback_positions([record])

    assert len(positions) == 1
    assert positions[0]["game_index"] == 1
    assert positions[0]["opening_index"] == 4
    assert positions[0]["move_index"] == 1
    assert positions[0]["game_ply"] == 1
    assert positions[0]["position_fen"] == board_to_fen(Board())


def test_tactics_smoke_is_marked_synthetic_and_evaluator_reports_metrics():
    candidates = positions_from_records([_game(24, plies=14)], min_ply=10, max_ply=14)
    suite = build_smoke_suite(candidates, count=3, labeler=FakeLabeler())

    report = evaluate_suite(suite, engine_spec="first", time_ms=10)

    assert suite["smoke_only"] is True
    assert suite["label_provenance"].startswith("synthetic")
    assert report["smoke_only"] is True
    assert report["overall"]["positions"] == 3
    assert 0 <= report["overall"]["solve_rate"] <= 1
    assert 0 <= report["overall"]["blunder_rate"] <= 1
    assert report["overall"]["mean_centipawn_loss"] >= 0


def test_tactics_builder_uses_hash_split_and_fake_labeler():
    candidates = positions_from_records(
        [_game(seed, plies=18) for seed in range(8)], min_ply=10, max_ply=18
    )
    dev_candidate = next(
        candidate for candidate in candidates if split_for_fen(candidate["fen"]) == "dev"
    )
    suite = build_tactics_suite(
        [dev_candidate],
        _HighMaterialFakeLabeler(),
        category_split_targets={"win_material": {"dev": 1, "test": 0}},
    )

    assert len(suite["positions"]) == 1
    position = suite["positions"][0]
    assert position["category"] == "win_material"
    assert position["split"] == "dev"
    assert position["label_depth"] == 25
    assert set(position["legal_moves"]) == {
        score["move"] for score in position["move_scores"]
    }


def test_tactics_builder_resumes_from_durable_checkpoint(tmp_path):
    candidates = positions_from_records(
        [_game(seed, plies=18) for seed in range(8)], min_ply=10, max_ply=18
    )
    candidate = next(
        item for item in candidates if split_for_fen(item["fen"]) == "dev"
    )
    checkpoint = tmp_path / "az_tac.checkpoint.jsonl"

    class CountingLabeler(_HighMaterialFakeLabeler):
        def __init__(self):
            self.calls = 0

        def label_position(self, fen, legal_moves):
            self.calls += 1
            return super().label_position(fen, legal_moves)

    first_labeler = CountingLabeler()
    first = build_tactics_suite(
        [candidate],
        first_labeler,
        category_split_targets={"win_material": {"dev": 1, "test": 0}},
        checkpoint_path=checkpoint,
    )
    assert len(first["positions"]) == 1
    assert first_labeler.calls == 1
    assert checkpoint.exists()
    assert len(checkpoint.read_text(encoding="utf-8").splitlines()) == 2

    resumed_labeler = CountingLabeler()
    resumed = build_tactics_suite(
        [candidate],
        resumed_labeler,
        category_split_targets={"win_material": {"dev": 1, "test": 0}},
        checkpoint_path=checkpoint,
    )
    assert resumed["positions"] == first["positions"]
    assert resumed_labeler.calls == 0


def test_tactics_checkpoint_rejects_changed_search_metadata(tmp_path):
    candidates = positions_from_records(
        [_game(seed, plies=12) for seed in range(8)], min_ply=10, max_ply=10
    )
    candidate = next(
        item for item in candidates if split_for_fen(item["fen"]) == "dev"
    )
    checkpoint = tmp_path / "az_tac.checkpoint.jsonl"
    target = {"win_material": {"dev": 1, "test": 0}}
    build_tactics_suite(
        [candidate],
        _HighMaterialFakeLabeler(),
        category_split_targets=target,
        checkpoint_path=checkpoint,
        checkpoint_metadata={"run": "first"},
    )
    with pytest.raises(ValueError, match="does not match current input"):
        build_tactics_suite(
            candidates,
            _HighMaterialFakeLabeler(),
            category_split_targets=target,
            checkpoint_path=checkpoint,
            checkpoint_metadata={"run": "changed"},
        )


def test_tactics_builder_rejects_incomplete_fake_labels():
    candidate = positions_from_records([_game(31, plies=12)], min_ply=10, max_ply=10)[0]

    class IncompleteLabeler:
        def label_position(self, fen, legal_moves):
            return {"scores": [], "top_moves": [], "best_move": None}

    with pytest.raises(ValueError, match="labeler must score each legal move"):
        build_tactics_suite(
            [candidate],
            IncompleteLabeler(),
            category_split_targets={"win_material": {"dev": 1, "test": 0}},
        )


def test_pikafish_root_labeler_reads_multipv_and_forced_root_scores():
    board = Board()
    fen = board_to_fen(board)
    legal_moves = [
        GameRecord.move_to_iccs(move)
        for move in Rule.generate_legal_moves(board, board.current_player)
    ]
    fixture = Path(__file__).parent / "fixtures" / "fake_multipv_engine.py"

    labeler = PikafishRootLabeler(
        [sys.executable, str(fixture)],
        top_depth=3,
        rest_depth=1,
        top_moves=3,
        threads=2,
    )
    with labeler:
        labels = labeler.label_position(fen, legal_moves)
        provenance = labeler.provenance()

    scores = {score["move"]: score for score in labels["scores"]}
    assert provenance["engine"] == "id name FakeMultiPV"
    assert provenance["binary_name"] == Path(sys.executable).name
    assert len(provenance["binary_sha256"]) == 64
    assert provenance["threads"] == 2
    assert set(scores) == set(legal_moves)
    assert len(labels["top_moves"]) == 3
    assert all(scores[move]["depth"] == 3 for move in labels["top_moves"])
    assert all(
        scores[move]["depth"] == 1
        for move in set(legal_moves) - set(labels["top_moves"])
    )


def test_search_tactics_evaluation_clears_transpositions_between_positions():
    candidates = positions_from_records([_game(88, plies=14)], min_ply=10, max_ply=14)
    suite = build_smoke_suite(candidates, count=3, labeler=FakeLabeler())

    class FakeEngine:
        def __init__(self):
            self.clears = 0
            self.tt = SimpleNamespace(clear=self._clear)

        def _clear(self):
            self.clears += 1

        def choose_move(self, board, color, stop_event):
            return SimpleNamespace(
                best_move=GameRecord.move_from_iccs(
                    GameRecord.move_to_iccs(
                        Rule.generate_legal_moves(board, color)[0]
                    )
                )
            )

    engine = FakeEngine()
    report = evaluate_suite(suite, engine_spec="search", time_ms=10, engine=engine)

    assert engine.clears == len(suite["positions"])
    assert report["overall"]["positions"] == len(suite["positions"])
