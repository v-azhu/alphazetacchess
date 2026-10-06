import random

import pytest

from alphazetacchess.core.board import Board
from alphazetacchess.core.rule import Rule
from alphazetacchess.selfplay.paired_openings import select_paired_openings
from tools.compare_engines_paired import _config_for_depth


def _record(seed):
    rng = random.Random(seed)
    board = Board()
    moves = []
    for _ in range(10):
        move = rng.choice(Rule.generate_legal_moves(board, board.current_player))
        moves.append({
            "color": board.current_player.name,
            "from": list(move.from_pos),
            "to": list(move.to_pos),
        })
        board.move(move.from_pos, move.to_pos)
    return {"moves": moves}


def test_select_paired_openings_is_reproducible_and_red_to_move():
    records = [_record(seed) for seed in range(5)]

    selected = select_paired_openings(records, opening_count=3, seed=17)
    repeated = select_paired_openings(records, opening_count=3, seed=17)

    assert selected == repeated
    assert len({opening["initial_fen"].split()[0] for opening in selected}) == 3
    for opening in selected:
        assert opening["initial_fen"].split()[1] == "w"
        assert len(opening["opening_prefix"]) == 10


def test_select_paired_openings_rejects_odd_ply_count():
    with pytest.raises(ValueError, match="even"):
        select_paired_openings([_record(1)], opening_count=1, opening_plies=9)


def test_select_paired_openings_rejects_insufficient_unique_positions():
    record = _record(1)

    with pytest.raises(ValueError, match="distinct legal openings"):
        select_paired_openings([record, record], opening_count=2, seed=2)


def test_paired_runner_uses_baseline_configs_for_external_game_records():
    depth4 = _config_for_depth([{"red_config": {"source": "external"}}], 4)
    depth3 = _config_for_depth([{"red_config": {"source": "external"}}], 3)

    assert depth4["depth"] == 4
    assert depth3["depth"] == 3
    assert depth4["engine"] == depth3["engine"] == "search"
    assert depth4["use_killer_moves"] is True
