"""Search limits shared by protocol adapters and future engine frontends."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SearchLimits:
    """Normalized limits for one search request.

    All time values are expressed in milliseconds after protocol parsing.
    ``deadline_ms`` is intentionally not stored here because it depends on
    when the search worker actually starts.
    """

    depth: Optional[int] = None
    movetime_ms: Optional[int] = None
    time_ms: Optional[int] = None
    opptime_ms: Optional[int] = None
    increment_ms: int = 0
    oppincrement_ms: int = 0
    movestogo: Optional[int] = None

    def __post_init__(self):
        for name in (
            "depth",
            "movetime_ms",
            "time_ms",
            "opptime_ms",
            "increment_ms",
            "oppincrement_ms",
            "movestogo",
        ):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative")

        if self.depth == 0:
            raise ValueError("depth must be greater than zero")
        if self.movestogo == 0:
            raise ValueError("movestogo must be greater than zero")

    def time_budget_ms(self):
        """Return a conservative budget for the side to move, if time exists."""
        if self.movetime_ms is not None:
            return self.movetime_ms

        if self.time_ms is None:
            return None

        moves = self.movestogo or 20
        base = self.time_ms / moves
        budget = base + self.increment_ms * 0.5

        # Keep a reserve for the remainder of the game and protocol overhead.
        return max(1, min(int(budget), max(1, int(self.time_ms * 0.8))))
