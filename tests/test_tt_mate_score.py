from alphazetacchess.engine.search import MATE_SCORE
from alphazetacchess.engine.transposition_table import Bound, TranspositionTable


def test_mate_score_is_normalized_across_search_plies():
    tt = TranspositionTable()
    mate_score = MATE_SCORE - 5

    tt.store("position", 4, mate_score, Bound.EXACT, None, ply=5)

    score, _ = tt.probe("position", 4, -MATE_SCORE, MATE_SCORE, ply=7)

    assert score == MATE_SCORE - 7


def test_mated_score_is_normalized_across_search_plies():
    tt = TranspositionTable()
    mated_score = -(MATE_SCORE - 5)

    tt.store("position", 4, mated_score, Bound.EXACT, None, ply=5)

    score, _ = tt.probe("position", 4, -MATE_SCORE, MATE_SCORE, ply=7)

    assert score == -(MATE_SCORE - 7)
