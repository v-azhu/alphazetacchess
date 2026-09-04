"""V0.5.3 endgame-phase heuristics tests (engine/endgame.py) and
self-play endgame-analysis tests (selfplay/endgame_analysis.py)."""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.evaluation import evaluate
from alphazetacchess.engine.endgame import (
    is_endgame,
    endgame_score,
    endgame_balance,
    ENDGAME_ROOK_BONUS,
    ENDGAME_CANNON_PENALTY,
    ENDGAME_MAJOR_MATERIAL_THRESHOLD,
)
from alphazetacchess.selfplay.endgame_analysis import (
    find_endgame_onset,
    summarize_endgame_outcomes,
)


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def put(board, piece_type, color, x, y):
    board.board[y][x] = Piece(piece_type, color, x, y)


# ---------------------------------------------------------------------------
# is_endgame
# ---------------------------------------------------------------------------

def test_starting_position_is_not_endgame():
    assert is_endgame(Board()) is False


def test_full_major_material_below_threshold_is_endgame():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.ROOK, Color.BLACK, 0, 9)

    assert 900 + 900 <= ENDGAME_MAJOR_MATERIAL_THRESHOLD
    assert is_endgame(board) is True


def test_bare_kings_is_endgame():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)

    assert is_endgame(board) is True


# ---------------------------------------------------------------------------
# endgame_score / endgame_balance
# ---------------------------------------------------------------------------

def test_endgame_score_is_zero_outside_endgame_phase():
    board = Board()  # starting position: not endgame

    assert endgame_score(board, Color.RED) == 0
    assert endgame_score(board, Color.BLACK) == 0


def test_endgame_score_rewards_rook_and_penalizes_cannon_when_in_endgame():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.CANNON, Color.RED, 1, 0)

    assert is_endgame(board) is True
    assert endgame_score(board, Color.RED) == ENDGAME_ROOK_BONUS + ENDGAME_CANNON_PENALTY
    assert endgame_score(board, Color.BLACK) == 0


def test_endgame_balance_is_symmetric_between_colors():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    put(board, PieceType.ROOK, Color.RED, 0, 0)
    put(board, PieceType.CANNON, Color.BLACK, 8, 9)

    assert endgame_balance(board, Color.RED) == -endgame_balance(board, Color.BLACK)


# ---------------------------------------------------------------------------
# evaluate() toggle
# ---------------------------------------------------------------------------

def test_endgame_heuristics_disabled_by_default_preserves_v052_evaluation():
    board = Board()

    baseline = evaluate(
        board, Color.RED,
        use_piece_square_tables=True, use_king_safety=True,
        use_mobility=False, use_pawn_structure=False,
        use_piece_coordination=False,
    )
    explicit_off = evaluate(
        board, Color.RED,
        use_piece_square_tables=True, use_king_safety=True,
        use_mobility=False, use_pawn_structure=False,
        use_piece_coordination=False, use_endgame_heuristics=False,
    )

    assert explicit_off == baseline


def test_endgame_heuristics_toggle_changes_evaluation_when_relevant():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    put(board, PieceType.ROOK, Color.RED, 0, 0)

    without = evaluate(
        board, Color.RED,
        use_piece_square_tables=False, use_king_safety=False,
        use_mobility=False, use_pawn_structure=False,
        use_piece_coordination=False, use_endgame_heuristics=False,
    )
    with_eg = evaluate(
        board, Color.RED,
        use_piece_square_tables=False, use_king_safety=False,
        use_mobility=False, use_pawn_structure=False,
        use_piece_coordination=False, use_endgame_heuristics=True,
    )

    assert with_eg - without == ENDGAME_ROOK_BONUS


def test_search_engine_use_endgame_heuristics_toggle_reaches_evaluation():
    from alphazetacchess.engine.search import SearchEngine

    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 4, 9)
    put(board, PieceType.ROOK, Color.RED, 0, 0)

    with_eg = SearchEngine(use_endgame_heuristics=True)
    without_eg = SearchEngine(use_endgame_heuristics=False)

    score_with = with_eg._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )
    score_without = without_eg._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )

    assert score_with == evaluate(board, Color.RED, use_endgame_heuristics=True)
    assert score_without == evaluate(board, Color.RED, use_endgame_heuristics=False)
    assert score_with != score_without


# ---------------------------------------------------------------------------
# selfplay/endgame_analysis.py
# ---------------------------------------------------------------------------

# A hand-built, capture-heavy 9-ply move list that walks the starting
# position down to major material 2250 (below ENDGAME_MAJOR_MATERIAL_
# THRESHOLD=2600) on exactly its last move. Board.move() doesn't
# validate legality, so these captures don't need to be reachable by
# real Xiangqi rules -- only the resulting material counts matter for
# exercising find_endgame_onset(). Verified independently by replaying
# it against a real Board() (see docs/v0.5.3.md).
_ONSET_AT_PLY_8_MOVES = [
    {"color": "RED", "from": [1, 0], "to": [1, 9]},
    {"color": "BLACK", "from": [1, 7], "to": [1, 2]},
    {"color": "RED", "from": [7, 0], "to": [7, 9]},
    {"color": "BLACK", "from": [7, 7], "to": [7, 2]},
    {"color": "RED", "from": [0, 0], "to": [0, 9]},
    {"color": "BLACK", "from": [8, 9], "to": [8, 0]},
    {"color": "RED", "from": [1, 9], "to": [1, 2]},
    {"color": "BLACK", "from": [7, 2], "to": [7, 9]},
    {"color": "BLACK", "from": [8, 0], "to": [1, 2]},
]


def test_find_endgame_onset_returns_none_when_never_reached():
    record = {"moves": []}

    assert find_endgame_onset(record) is None


def test_find_endgame_onset_finds_the_correct_ply():
    record = {"moves": _ONSET_AT_PLY_8_MOVES}

    onset = find_endgame_onset(record)

    assert onset is not None
    assert onset["ply"] == 8


def test_summarize_endgame_outcomes_counts_reached_and_never_reached_games():
    records = [
        {"moves": [], "result": "DRAW"},
        {"moves": _ONSET_AT_PLY_8_MOVES, "result": "BLACK_WINS"},
    ]

    stats = summarize_endgame_outcomes(records)

    assert stats["games"] == 2
    assert stats["reached_endgame"] == 1
    assert stats["avg_onset_ply"] == 8


def test_summarize_endgame_outcomes_credits_the_edge_favored_side_correctly():
    # At the ply-8 onset of _ONSET_AT_PLY_8_MOVES, RED holds one Rook
    # and no Cannons; BLACK holds one Rook AND one Cannon. Equal Rook
    # counts cancel out, so the only difference is BLACK's extra
    # Cannon -- which is a *penalty* under engine/endgame.py's
    # weighting, not a bonus. Net edge = ENDGAME_CANNON_PENALTY * (0 - 1)
    # = +40, i.e. positive/RED-favored, precisely because having an
    # extra Cannon in the endgame is a liability, not an asset.
    black_wins = {"moves": _ONSET_AT_PLY_8_MOVES, "result": "BLACK_WINS"}
    red_wins = {"moves": _ONSET_AT_PLY_8_MOVES, "result": "RED_WINS"}

    stats_loss = summarize_endgame_outcomes([black_wins])
    stats_win = summarize_endgame_outcomes([red_wins])

    assert stats_loss["edge_favored_wins"] == 0
    assert stats_loss["edge_favored_losses"] == 1

    assert stats_win["edge_favored_wins"] == 1
    assert stats_win["edge_favored_losses"] == 0
