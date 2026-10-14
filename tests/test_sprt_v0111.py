"""Tests for the pure-Python pentanomial SPRT."""
import math

import pytest

from alphazetacchess.selfplay.sprt import (
    PAIR_SCORES,
    PentanomialSPRT,
    SPRTState,
    monte_carlo_rates,
    pentanomial_probabilities,
)


def test_pair_probabilities_sum_to_one_and_are_symmetric_at_zero_elo():
    probs = pentanomial_probabilities(0.0, draw_rate=0.2)
    assert sum(probs) == pytest.approx(1.0)
    assert probs == pytest.approx(tuple(reversed(probs)))


def test_llr_matches_independent_hand_computed_reference():
    test = PentanomialSPRT(0.0, 10.0, draw_rate=0.2, max_games=200)
    observations = [0.0, 0.5, 1.0, 1.5, 2.0, 1.0]
    p0 = pentanomial_probabilities(0.0, 0.2)
    p1 = pentanomial_probabilities(10.0, 0.2)
    expected = 0.0
    for observation in observations:
        index = PAIR_SCORES.index(observation)
        expected += math.log(p1[index] / p0[index])
        result = test.update(observation)
        assert result.llr == pytest.approx(expected, abs=1e-12)


def test_invalid_pair_score_is_rejected():
    test = PentanomialSPRT(0, 10)
    with pytest.raises(ValueError):
        test.update(0.75)


def test_identical_pair_scores_are_reported_as_degenerate():
    test = PentanomialSPRT(0, 10, max_games=100)
    result = None
    for _ in range(20):
        result = test.update(1.0)
        if result.state != SPRTState.CONTINUE:
            break
    assert result is not None
    assert result.state == SPRTState.INCONCLUSIVE
    assert "zero observed variance" in result.reason


def test_monte_carlo_type_i_error_at_h0_boundary():
    rates = monte_carlo_rates(
        elo=0.0, h0_elo=0.0, h1_elo=10.0, tests=10_000, seed=20261013,
        draw_rate=0.2, max_games=8000,
    )
    # Finite-sample tolerance is deliberately stated rather than hidden.
    assert rates["ACCEPT_H1"] <= 0.065


def test_monte_carlo_power_at_h1_boundary():
    rates = monte_carlo_rates(
        elo=10.0, h0_elo=0.0, h1_elo=10.0, tests=10_000, seed=20261014,
        draw_rate=0.2, max_games=8000,
    )
    assert rates["ACCEPT_H1"] >= 0.935
