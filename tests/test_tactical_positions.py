from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.piece import Color, PieceType
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.engine.transposition_table import MATE_SCORE


TACTICAL_POSITIONS = {
    "mate_in_one": {
        # Red is not in check. Red's horse can move 5,6 -> 5,7,
        # checking the Black king. This is based on the existing
        # checkmate pattern covered by test_rule.py. The extra Black
        # pawn on 0,6 gives Black a legal move before the mate, so the
        # initial position is not already stalemate.
        "fen": "3aka3/4b4/9/p4N3/9/9/9/9/9/4K4 w - - 0 1",
        "side": Color.RED,
        "pieces": {
            (4, 9): (Color.BLACK, PieceType.KING),
            (5, 6): (Color.RED, PieceType.HORSE),
            (4, 0): (Color.RED, PieceType.KING),
        },
    },
    "free_capture": {
        "fen": "4k4/9/9/R3n4/9/9/9/9/9/4K4 w - - 0 1",
        "side": Color.RED,
        "pieces": {
            (4, 9): (Color.BLACK, PieceType.KING),
            (0, 6): (Color.RED, PieceType.ROOK),
            (4, 6): (Color.BLACK, PieceType.HORSE),
            (4, 0): (Color.RED, PieceType.KING),
        },
    },
    "exchange_trap": {
        # Red can capture the Black pawn at (0,1), but the Black rook
        # at (1,1) can immediately recapture the Red rook. The Black
        # king is at (2,9), deliberately avoiding both the flying-general
        # relation with the Red king and the vertical check created by
        # Red moving the rook to (3,0).
        "fen": "2k6/9/9/9/9/9/9/9/pr7/R3K4 w - - 0 1",
        "side": Color.RED,
        "pieces": {
            (2, 9): (Color.BLACK, PieceType.KING),
            (1, 1): (Color.BLACK, PieceType.ROOK),
            (0, 1): (Color.BLACK, PieceType.PAWN),
            (0, 0): (Color.RED, PieceType.ROOK),
            (4, 0): (Color.RED, PieceType.KING),
        },
    },
}


def _move(board, from_pos, to_pos):
    return next(
        move
        for move in Rule.generate_legal_moves(board, board.current_player)
        if move.from_pos == from_pos and move.to_pos == to_pos
    )


def immediate_mates(board, color):
    """Return legal moves that leave the opponent checkmated."""
    mates = []
    for move in Rule.generate_legal_moves(board, color):
        board.move(move.from_pos, move.to_pos)
        try:
            opponent = board.opponent(color)
            if Rule.is_checkmate(board, opponent):
                mates.append(move)
        finally:
            board.undo()
    return mates


def capture_targets(board, color, recapturable):
    targets = []
    for move in Rule.generate_legal_moves(board, color):
        if move.captured_piece is None:
            continue
        board.move(move.from_pos, move.to_pos)
        try:
            opponent = board.opponent(color)
            can_recapture = any(
                reply.to_pos == move.to_pos
                for reply in Rule.generate_legal_moves(board, opponent)
            )
            if can_recapture == recapturable:
                targets.append(move)
        finally:
            board.undo()
    return targets


def assert_expected_pieces(board, expected):
    """Verify fixture geometry independently from the FEN comments."""
    for position, (color, piece_type) in expected.items():
        x, y = position
        piece = board.get(x, y)
        assert piece is not None, f"expected {color} {piece_type} at {position}"
        assert piece.color == color, f"wrong color at {position}: {piece}"
        assert piece.type == piece_type, f"wrong type at {position}: {piece}"


def test_tactical_fixtures_are_legal_and_have_expected_objective_property():
    for spec in TACTICAL_POSITIONS.values():
        board = board_from_fen(spec["fen"])
        assert_expected_pieces(board, spec["pieces"])
        assert not Rule.is_in_check(board, spec["side"])

    mate_board = board_from_fen(TACTICAL_POSITIONS["mate_in_one"]["fen"])
    mates = immediate_mates(mate_board, Color.RED)
    assert mates

    free_board = board_from_fen(TACTICAL_POSITIONS["free_capture"]["fen"])
    capture = _move(free_board, (0, 6), (4, 6))
    assert capture.captured_piece is not None
    free_board.move(capture.from_pos, capture.to_pos)
    try:
        opponent_captures = [
            move
            for move in Rule.generate_legal_moves(free_board, Color.BLACK)
            if move.to_pos == capture.to_pos
        ]
        assert not opponent_captures
    finally:
        free_board.undo()

    trap_board = board_from_fen(TACTICAL_POSITIONS["exchange_trap"]["fen"])
    assert Rule.is_checkmate(trap_board, Color.BLACK) is False
    assert Rule.is_stalemate(trap_board, Color.BLACK) is False

    capture = _move(trap_board, (0, 0), (0, 1))
    assert capture.captured_piece is not None
    trap_board.move(capture.from_pos, capture.to_pos)
    try:
        opponent_captures = [
            move
            for move in Rule.generate_legal_moves(trap_board, Color.BLACK)
            if move.to_pos == capture.to_pos
        ]
        assert opponent_captures
        assert any(
            move.from_pos == (1, 1) and move.to_pos == (0, 1)
            for move in opponent_captures
        )
    finally:
        trap_board.undo()


def test_mate_in_one_fixture_has_no_hidden_mate_before_the_move():
    board = board_from_fen(TACTICAL_POSITIONS["mate_in_one"]["fen"])
    assert Rule.is_checkmate(board, Color.BLACK) is False
    assert Rule.is_stalemate(board, Color.BLACK) is False


def test_tactical_helpers_restore_board_state():
    board = board_from_fen(TACTICAL_POSITIONS["mate_in_one"]["fen"])
    before_hash = board.zobrist_hash
    before_player = board.current_player

    immediate_mates(board, Color.RED)

    assert board.zobrist_hash == before_hash
    assert board.current_player == before_player


def test_search_respects_objectively_checked_tactical_properties():
    mate_board = board_from_fen(TACTICAL_POSITIONS["mate_in_one"]["fen"])
    mate_moves = {
        (move.from_pos, move.to_pos)
        for move in immediate_mates(mate_board, Color.RED)
    }
    mate_result = SearchEngine(depth=2).choose_move(mate_board, Color.RED)
    assert (mate_result.best_move.from_pos, mate_result.best_move.to_pos) in mate_moves

    free_board = board_from_fen(TACTICAL_POSITIONS["free_capture"]["fen"])
    safe_captures = {
        (move.from_pos, move.to_pos)
        for move in capture_targets(free_board, Color.RED, recapturable=False)
    }
    free_result = SearchEngine(depth=2).choose_move(free_board, Color.RED)
    assert (free_result.best_move.from_pos, free_result.best_move.to_pos) in safe_captures


def test_quiescence_check_extension_finds_the_fixture_mate_in_one():
    board = board_from_fen(TACTICAL_POSITIONS["mate_in_one"]["fen"])
    before_hash = board.zobrist_hash
    baseline = SearchEngine(quiescence_check_plies=0)._quiescence(
        board, float("-inf"), float("inf"), Color.RED, 0, 0
    )
    extended = SearchEngine(quiescence_check_plies=1)._quiescence(
        board, float("-inf"), float("inf"), Color.RED, 0, 0
    )

    assert baseline < MATE_SCORE - 1
    assert extended == MATE_SCORE - 1
    assert board.zobrist_hash == before_hash


def test_quiescence_check_extension_sees_forced_mate_after_capture():
    board = board_from_fen(TACTICAL_POSITIONS["free_capture"]["fen"])
    capture = _move(board, (0, 6), (4, 6))
    board.move(capture.from_pos, capture.to_pos)
    try:
        replies = Rule.generate_legal_moves(board, Color.BLACK)
        assert len(replies) == 2
        for reply in replies:
            board.move(reply.from_pos, reply.to_pos)
            try:
                assert immediate_mates(board, Color.RED)
            finally:
                board.undo()
    finally:
        board.undo()

    baseline = SearchEngine(depth=2, use_null_move=False).choose_move(
        board, Color.RED
    )
    extended = SearchEngine(
        depth=2,
        use_null_move=False,
        quiescence_check_plies=1,
    ).choose_move(board, Color.RED)

    assert (extended.best_move.from_pos, extended.best_move.to_pos) == (
        (0, 6), (4, 6)
    )
    assert baseline.score < MATE_SCORE - 3
    assert extended.score == MATE_SCORE - 3

    trap_board = board_from_fen(TACTICAL_POSITIONS["exchange_trap"]["fen"])
    unsafe_captures = {
        (move.from_pos, move.to_pos)
        for move in capture_targets(trap_board, Color.RED, recapturable=True)
    }
    trap_result = SearchEngine(depth=2).choose_move(trap_board, Color.RED)
    assert (trap_result.best_move.from_pos, trap_result.best_move.to_pos) not in unsafe_captures
