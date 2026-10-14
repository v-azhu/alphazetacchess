"""Pentanomial generalized SPRT for paired Xiangqi engine matches.

Each opening pair consists of two games with colors swapped. The candidate's
pair score is one of {0, 0.5, 1, 1.5, 2}. A fixed draw-rate nuisance parameter
maps an Elo hypothesis to game W/D/L probabilities; the pair probabilities
are the convolution of those game-score probabilities.

This module is pure Python and has no engine or filesystem dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import random
from typing import Iterable, Sequence


PAIR_SCORES = (0.0, 0.5, 1.0, 1.5, 2.0)


class SPRTState(str, Enum):
    CONTINUE = "CONTINUE"
    ACCEPT_H1 = "ACCEPT_H1"
    ACCEPT_H0 = "ACCEPT_H0"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class Gate:
    name: str
    h0_elo: float
    h1_elo: float
    max_games: int


GATES = {
    "G1": Gate("G1", -10.0, 0.0, 8000),
    "G2": Gate("G2", 0.0, 10.0, 8000),
    "G3": Gate("G3", 50.0, 150.0, 1000),
}


@dataclass(frozen=True)
class SPRTResult:
    state: SPRTState
    llr: float
    lower_bound: float
    upper_bound: float
    pairs: int
    games: int
    pair_counts: tuple[int, int, int, int, int]
    reason: str | None = None


def logistic_score(elo: float) -> float:
    """Expected score per game for an Elo difference."""
    exponent = -float(elo) * math.log(10.0) / 400.0
    if exponent >= 0:
        e = math.exp(-exponent)
        return e / (1.0 + e)
    e = math.exp(exponent)
    return 1.0 / (1.0 + e)


def game_outcome_probabilities(elo: float, draw_rate: float = 0.2) -> tuple[float, float, float]:
    """Return (loss, draw, win) probabilities for the candidate.

    Draw rate is a nuisance parameter fixed across H0/H1; it must be in [0, 1).
    Elo determines expected score using the standard logistic model.
    """
    if not 0.0 <= draw_rate < 1.0:
        raise ValueError("draw_rate must be in [0, 1)")
    score = logistic_score(elo)
    win = score - draw_rate / 2.0
    loss = 1.0 - score - draw_rate / 2.0
    # A high draw rate can make extreme Elo hypotheses infeasible.
    if loss < 0.0 or win < 0.0:
        raise ValueError(
            f"draw_rate={draw_rate} is incompatible with Elo hypothesis {elo}"
        )
    return loss, draw_rate, win


def pentanomial_probabilities(elo: float, draw_rate: float = 0.2) -> tuple[float, ...]:
    """Probability mass for candidate pair scores 0, .5, 1, 1.5, 2."""
    loss, draw, win = game_outcome_probabilities(elo, draw_rate)
    # Single-game scores are 0, .5, 1. Pair scores are their convolution.
    single = (loss, draw, win)
    pair = [0.0] * 5
    for i, p in enumerate(single):
        for j, q in enumerate(single):
            pair[i + j] += p * q
    total = sum(pair)
    return tuple(p / total for p in pair)


def _bounds(alpha: float, beta: float) -> tuple[float, float]:
    if not 0.0 < alpha < 1.0 or not 0.0 < beta < 1.0:
        raise ValueError("alpha and beta must be strictly between 0 and 1")
    return math.log(beta / (1.0 - alpha)), math.log((1.0 - beta) / alpha)


class PentanomialSPRT:
    """Sequential likelihood-ratio test for paired-opening score observations."""

    def __init__(
        self,
        h0_elo: float,
        h1_elo: float,
        *,
        alpha: float = 0.05,
        beta: float = 0.05,
        draw_rate: float = 0.2,
        max_games: int = 8000,
    ):
        if h0_elo == h1_elo:
            raise ValueError("H0 and H1 Elo hypotheses must differ")
        if max_games < 2 or max_games % 2:
            raise ValueError("max_games must be an even integer >= 2")
        self.h0_elo = float(h0_elo)
        self.h1_elo = float(h1_elo)
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.draw_rate = float(draw_rate)
        self.max_pairs = max_games // 2
        self.lower_bound, self.upper_bound = _bounds(alpha, beta)
        self.p0 = pentanomial_probabilities(self.h0_elo, draw_rate)
        self.p1 = pentanomial_probabilities(self.h1_elo, draw_rate)
        self._counts = [0] * 5
        self._llr = 0.0
        self._state = SPRTState.CONTINUE
        self._reason = None

    @property
    def llr(self) -> float:
        return self._llr

    @property
    def pairs(self) -> int:
        return sum(self._counts)

    @property
    def games(self) -> int:
        return 2 * self.pairs

    @property
    def state(self) -> SPRTState:
        return self._state

    def update(self, pair_score: float) -> SPRTResult:
        """Consume one candidate pair score; game cap is measured in games."""
        if self._state != SPRTState.CONTINUE:
            raise RuntimeError(f"SPRT already stopped: {self._state.value}")
        try:
            index = PAIR_SCORES.index(float(pair_score))
        except ValueError as exc:
            raise ValueError(f"pair_score must be one of {PAIR_SCORES}") from exc
        self._counts[index] += 1
        p0, p1 = self.p0[index], self.p1[index]
        if p0 <= 0.0 or p1 <= 0.0:
            self._state = SPRTState.INCONCLUSIVE
            self._reason = "degenerate probability under H0 or H1; LLR undefined"
            return self.result()
        self._llr += math.log(p1 / p0)
        if self._llr >= self.upper_bound:
            self._state = SPRTState.ACCEPT_H1
        elif self._llr <= self.lower_bound:
            self._state = SPRTState.ACCEPT_H0
        elif self.games >= self.max_pairs * 2:
            self._state = SPRTState.INCONCLUSIVE
            self._reason = "game cap reached before either likelihood boundary"
        return self.result()

    def result(self) -> SPRTResult:
        return SPRTResult(
            state=self._state,
            llr=self._llr,
            lower_bound=self.lower_bound,
            upper_bound=self.upper_bound,
            pairs=self.pairs,
            games=self.games,
            pair_counts=tuple(self._counts),
            reason=self._reason,
        )


def simulate_test(
    elo: float,
    h0_elo: float,
    h1_elo: float,
    *,
    draw_rate: float = 0.2,
    alpha: float = 0.05,
    beta: float = 0.05,
    max_games: int = 8000,
    seed: int = 0,
) -> SPRTState:
    """Run one simulated test with deterministic randomness for a given seed."""
    rng = random.Random(seed)
    probabilities = pentanomial_probabilities(elo, draw_rate)
    cumulative = []
    running = 0.0
    for p in probabilities:
        running += p
        cumulative.append(running)
    test = PentanomialSPRT(
        h0_elo, h1_elo, alpha=alpha, beta=beta,
        draw_rate=draw_rate, max_games=max_games,
    )
    while test.state == SPRTState.CONTINUE:
        sample = rng.random()
        outcome = next(i for i, edge in enumerate(cumulative) if sample <= edge)
        test.update(PAIR_SCORES[outcome])
    return test.state


def monte_carlo_rates(
    elo: float,
    h0_elo: float,
    h1_elo: float,
    *,
    tests: int = 10_000,
    seed: int = 0,
    **kwargs,
) -> dict[str, float]:
    """Estimate accept-H1/H0/inconclusive rates over independent simulated tests."""
    if tests < 1:
        raise ValueError("tests must be positive")
    rng = random.Random(seed)
    counts = {state: 0 for state in SPRTState}
    for _ in range(tests):
        state = simulate_test(
            elo, h0_elo, h1_elo, seed=rng.randrange(2**63), **kwargs
        )
        counts[state] += 1
    return {state.value: counts[state] / tests for state in SPRTState}
