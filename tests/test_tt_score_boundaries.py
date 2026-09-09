from alphazetacchess.engine.search import MATE_SCORE
from alphazetacchess.engine.transposition_table import Bound, TranspositionTable


def test_non_mate_score_is_unchanged_by_normalization():
    tt = TranspositionTable()
    score = MATE_SCORE - 1001

    tt.store("position", 4, score, Bound.EXACT, None, ply=37)
    restored, _ = tt.probe(
        "position",
        4,
        -MATE_SCORE,
        MATE_SCORE,
        ply=37,
    )

    assert restored == score


def test_positive_mate_score_is_normalized_at_threshold_boundary():
    tt = TranspositionTable()
    score = MATE_SCORE - 1000

    tt.store("position", 4, score, Bound.EXACT, None, ply=5)
    restored, _ = tt.probe(
        "position",
        4,
        -MATE_SCORE,
        MATE_SCORE,
        ply=17,
    )

    assert restored == MATE_SCORE - 17


def test_negative_mate_score_is_normalized_at_threshold_boundary():
    tt = TranspositionTable()
    score = -(MATE_SCORE - 1000)

    tt.store("position", 4, score, Bound.EXACT, None, ply=5)
    restored, _ = tt.probe(
        "position",
        4,
        -MATE_SCORE,
        MATE_SCORE,
        ply=17,
    )

    assert restored == -(MATE_SCORE - 17)


def test_positive_mate_score_round_trip_at_ply_zero():
    tt = TranspositionTable()
    score = MATE_SCORE - 1

    tt.store("position", 4, score, Bound.EXACT, None, ply=0)
    restored, _ = tt.probe(
        "position",
        4,
        -MATE_SCORE,
        MATE_SCORE,
        ply=0,
    )

    assert restored == score


def test_negative_mate_score_round_trip_at_ply_zero():
    tt = TranspositionTable()
    score = -(MATE_SCORE - 1)

    tt.store("position", 4, score, Bound.EXACT, None, ply=0)
    restored, _ = tt.probe(
        "position",
        4,
        -MATE_SCORE,
        MATE_SCORE,
        ply=0,
    )

    assert restored == score


def test_lower_bound_mate_score_is_normalized_before_cutoff():
    tt = TranspositionTable()
    score = MATE_SCORE - 5

    tt.store("position", 4, score, Bound.LOWER, None, ply=5)

    restored, _ = tt.probe(
        "position",
        4,
        -MATE_SCORE,
        MATE_SCORE - 6,
        ply=7,
    )

    assert restored == score - 2
    assert tt.cutoffs == 1


def test_upper_bound_mate_score_is_normalized_before_cutoff():
    tt = TranspositionTable()
    score = -(MATE_SCORE - 5)

    tt.store("position", 4, score, Bound.UPPER, None, ply=5)

    restored, _ = tt.probe(
        "position",
        4,
        -(MATE_SCORE - 6),
        MATE_SCORE,
        ply=7,
    )

    assert restored == score + 2
    assert tt.cutoffs == 1
