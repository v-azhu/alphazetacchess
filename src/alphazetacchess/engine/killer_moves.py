class KillerMoves:
    """Two-slot killer-move table indexed by search ply.

    Killer moves are quiet moves that previously caused a beta cutoff at
    the same ply. The table is search-local: callers should clear it at
    the start of a new root search so moves from an unrelated position
    cannot affect ordering.
    """

    SLOTS = 2

    def __init__(self):
        self._table = {}

    def clear(self):
        self._table.clear()

    def get(self, ply):
        return tuple(self._table.get(ply, ()))

    def record(self, ply, move):
        """Record a quiet move that caused a beta cutoff.

        A move is identified by its from/to coordinates. Captures are never
        stored as killer moves because capture ordering has its own logic.
        """
        if move is None or move.captured_piece is not None:
            return

        key = (move.from_pos, move.to_pos)
        slots = self._table.setdefault(ply, [])
        if key in slots:
            slots.remove(key)
        slots.insert(0, key)
        del slots[self.SLOTS:]
