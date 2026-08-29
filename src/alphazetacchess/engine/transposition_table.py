"""Transposition table for AlphaZetaChess V0.3.2."""

from dataclasses import dataclass
from enum import Enum


class Bound(Enum):
    EXACT = 0
    LOWER = 1
    UPPER = 2


@dataclass(frozen=True)
class TTEntry:
    depth: int
    score: float
    bound: Bound
    best_move: tuple | None


class TranspositionTable:
    def __init__(self, max_entries=200_000):
        self.max_entries = max_entries
        self._table = {}
        self.hits = 0
        self.probes = 0
        self.cutoffs = 0

    def clear(self):
        self._table.clear()
        self.reset_stats()

    def reset_stats(self):
        self.hits = 0
        self.probes = 0
        self.cutoffs = 0

    def __len__(self):
        return len(self._table)

    def probe(self, key, depth, alpha, beta):
        self.probes += 1
        entry = self._table.get(key)

        if entry is None:
            return None, None

        self.hits += 1
        preferred_move = entry.best_move

        if entry.depth < depth:
            return None, preferred_move

        if entry.bound is Bound.EXACT:
            self.cutoffs += 1
            return entry.score, preferred_move

        if entry.bound is Bound.LOWER and entry.score >= beta:
            self.cutoffs += 1
            return entry.score, preferred_move

        if entry.bound is Bound.UPPER and entry.score <= alpha:
            self.cutoffs += 1
            return entry.score, preferred_move

        return None, preferred_move

    def store(self, key, depth, score, bound, best_move):
        move_key = None
        if best_move is not None:
            move_key = (best_move.from_pos, best_move.to_pos)

        old = self._table.get(key)

        # Prefer deeper entries. At equal depth, replace old data so a
        # newer bound / principal move can improve move ordering.
        if old is not None and old.depth > depth:
            return

        if len(self._table) >= self.max_entries and key not in self._table:
            # Simple deterministic eviction. A stronger replacement policy
            # can be introduced after V0.3.2 benchmarking.
            self._table.pop(next(iter(self._table)))

        self._table[key] = TTEntry(
            depth=depth,
            score=score,
            bound=bound,
            best_move=move_key,
        )
