from alphazetacchess.engine.history_heuristic import HistoryHeuristic


def test_history_rewards_quiet_move():
    class Move:
        from_pos = (0, 0)
        to_pos = (0, 1)
        captured_piece = None

    history = HistoryHeuristic()
    move = Move()
    assert history.get(move) == 0
    history.reward(move, 3)
    assert history.get(move) > 0


def test_history_penalizes_quiet_move():
    class Move:
        from_pos = (0, 0)
        to_pos = (0, 1)
        captured_piece = None

    history = HistoryHeuristic()
    move = Move()
    history.penalize(move, 3)
    assert history.get(move) < 0


def test_history_ignores_captures():
    class Piece:
        type = "pawn"

    class Move:
        from_pos = (0, 0)
        to_pos = (0, 1)
        captured_piece = Piece()

    history = HistoryHeuristic()
    move = Move()
    history.reward(move, 5)
    assert history.get(move) == 0


def test_history_stays_bounded():
    class Move:
        from_pos = (0, 0)
        to_pos = (0, 1)
        captured_piece = None

    history = HistoryHeuristic()
    move = Move()
    for _ in range(1000):
        history.reward(move, 20)
    assert history.get(move) <= history.MAX_SCORE
