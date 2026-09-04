"""V0.5.2b opening randomization for self-play data diversity.

A fully deterministic SearchEngine always makes identical moves from
identical positions. Confirmed directly from a real 10-game self-play
batch (depth=2, both sides identically configured, from the fixed
starting position): all 10 games were byte-for-byte identical, 82
moves each, same result. See docs/v0.5.2.md's "Known limitation" and
docs/v0.5.3-data-check.md for the full writeup -- naive self-play like
this produces zero usable diversity for an opening book or any other
statistical learning from self-play.

RandomizedOpeningEngine wraps any ChessEngine and, for the first
`random_plies` plies of a game, has `random_prob` probability of
playing a uniformly random legal move instead of the wrapped engine's
choice -- otherwise defers to the wrapped engine as normal. This is a
standard, simple technique ("epsilon-greedy exploration") for injecting
game diversity into self-play data collection without touching the
underlying search engine at all. Deliberately NOT built into
SearchEngine itself -- this is purely a data-collection concern, not a
playing-strength one, and keeping it as an external wrapper means a
"real" (non-randomized) game against this engine is unaffected.
"""

import random

from ..core.rule import Rule
from ..engine.base import ChessEngine, SearchResult


class RandomizedOpeningEngine(ChessEngine):
    def __init__(self, engine, random_plies=10, random_prob=0.3, rng=None):
        self.engine = engine
        self.random_plies = random_plies
        self.random_prob = random_prob
        self.rng = rng or random.Random()
        self.ply_count = 0

    def choose_move(self, board, color):
        self.ply_count += 1

        if self.ply_count <= self.random_plies and self.rng.random() < self.random_prob:
            legal_moves = Rule.generate_legal_moves(board, color)
            if legal_moves:
                move = self.rng.choice(legal_moves)
                return SearchResult(move, None, 0, 0)

        return self.engine.choose_move(board, color)
