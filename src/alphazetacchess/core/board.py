from .piece import Piece, PieceType, Color
from .zobrist import Zobrist


class Board:
    WIDTH = 9
    HEIGHT = 10

    PALACE_X = (3, 4, 5)
    RED_PALACE_Y = (0, 1, 2)
    BLACK_PALACE_Y = (7, 8, 9)

    def __init__(self):
        self.board = [
            [None for _ in range(self.WIDTH)]
            for _ in range(self.HEIGHT)
        ]
        # Move history is used by undo(). Position history stores the
        # incremental Zobrist key after every ply, including the initial
        # position. The side-to-move bit is part of the key, so this is an
        # exact-position history rather than a board-only repetition check.
        self.history = []
        self.position_history = []
        self.current_player = Color.RED
        # V0.9.9: see find_king() -- populated lazily on first lookup,
        # self-healing, so it needs no maintenance in move()/undo().
        self._king_cache = {}
        self.setup()
        self.zobrist_hash = Zobrist.board_hash(self)
        self.position_history.append(self.zobrist_hash)

    def setup(self):
        self._place_back_rank(0, Color.RED)
        self._place_cannon(2, Color.RED)
        for x in [0, 2, 4, 6, 8]:
            self._place(Piece(PieceType.PAWN, Color.RED, x, 3))

        self._place_back_rank(9, Color.BLACK)
        self._place_cannon(7, Color.BLACK)
        for x in [0, 2, 4, 6, 8]:
            self._place(Piece(PieceType.PAWN, Color.BLACK, x, 6))

    def _place(self, piece):
        self.board[piece.y][piece.x] = piece

    def _place_back_rank(self, y, color):
        pieces = [
            PieceType.ROOK,
            PieceType.HORSE,
            PieceType.ELEPHANT,
            PieceType.ADVISOR,
            PieceType.KING,
            PieceType.ADVISOR,
            PieceType.ELEPHANT,
            PieceType.HORSE,
            PieceType.ROOK,
        ]
        for x, p in enumerate(pieces):
            self._place(Piece(p, color, x, y))

    def _place_cannon(self, y, color):
        self._place(Piece(PieceType.CANNON, color, 1, y))
        self._place(Piece(PieceType.CANNON, color, 7, y))

    def get(self, x, y):
        return self.board[y][x]

    @staticmethod
    def in_bounds(x, y):
        return 0 <= x < Board.WIDTH and 0 <= y < Board.HEIGHT

    @staticmethod
    def in_palace(x, y, color):
        if x not in Board.PALACE_X:
            return False
        if color == Color.RED:
            return y in Board.RED_PALACE_Y
        return y in Board.BLACK_PALACE_Y

    @staticmethod
    def has_crossed_river(y, color):
        if color == Color.RED:
            return y >= 5
        return y <= 4

    @staticmethod
    def opponent(color):
        return Color.BLACK if color == Color.RED else Color.RED

    def find_king(self, color):
        """Locate `color`'s King.

        V0.9.9: O(1) in the common case via a cached `Piece` reference,
        instead of the full up-to-90-square scan this used to do on
        every call. Profiling a depth-3 search showed this being called
        470,284 times (via `is_in_check`/`kings_facing` inside
        `generate_legal_moves`'s per-move legality check) -- it was one
        of the largest single costs in the whole engine.

        The cache stores the King `Piece` object itself, not its
        coordinates, which is what makes this safe: `Board.move()`
        mutates `piece.x`/`piece.y` in place, so a cached King's
        coordinates stay correct across moves automatically, with no
        cache-invalidation needed on the hot path.

        The `self.board[y][x] is cached` guard makes it *self-healing*
        rather than merely fast: it re-scans whenever the cached piece
        isn't actually sitting where it thinks it is. That covers a
        King being captured, a board rebuilt or hand-edited in place
        (several tests do exactly this -- e.g. assigning
        `board.board = [[None, ...]]` or clearing a square directly),
        and `undo()` restoring a captured King. A cache that trusted
        coordinates alone, or that only invalidated inside `move()`,
        would silently return a stale King in all of those cases.
        """
        cached = self._king_cache.get(color)
        if cached is not None and self.board[cached.y][cached.x] is cached:
            return cached

        for row in self.board:
            for piece in row:
                if (
                    piece is not None
                    and piece.type == PieceType.KING
                    and piece.color == color
                ):
                    self._king_cache[color] = piece
                    return piece

        self._king_cache[color] = None
        return None

    def kings_facing(self):
        red_king = self.find_king(Color.RED)
        black_king = self.find_king(Color.BLACK)

        if red_king is None or black_king is None:
            return False
        if red_king.x != black_king.x:
            return False

        x = red_king.x
        y_low, y_high = sorted([red_king.y, black_king.y])

        for y in range(y_low + 1, y_high):
            if self.get(x, y) is not None:
                return False

        return True

    def probe_move(self, from_pos, to_pos):
        """V0.9.9: a deliberately minimal make-move used ONLY for
        legality probing (see `Rule.generate_legal_moves`), paired with
        `undo_probe`.

        `move()` maintains a lot of state a legality probe doesn't
        need: four Zobrist `PIECE_KEYS` lookups (each hashing a
        4-tuple containing two enums -- genuinely expensive in Python),
        the side-to-move flip, and appends to both `history` and
        `position_history`. Profiling showed `generate_legal_moves`
        driving 156,554 make/unmake pairs in a single depth-3 search,
        making all of that bookkeeping one of the engine's largest
        costs -- and every bit of it is discarded microseconds later
        when the probe is undone.

        A probe only needs what the attack detector actually reads:
        the board array, and the moved piece's own `x`/`y`. So that is
        all this touches.

        **This is not a general-purpose move.** It deliberately leaves
        `zobrist_hash`, `current_player`, `history` and
        `position_history` untouched, so the board is NOT in a
        coherent post-move state -- anything that reads those (the
        transposition table, repetition detection, `undo()`) would be
        silently wrong. It must be paired with `undo_probe` before the
        board is used for anything else, which is why both are kept
        private to the legality-check path rather than exposed as a
        faster general `move()`.
        """
        fx, fy = from_pos
        tx, ty = to_pos
        piece = self.board[fy][fx]
        captured = self.board[ty][tx]

        self.board[ty][tx] = piece
        self.board[fy][fx] = None
        if piece is not None:
            piece.x, piece.y = tx, ty

        return piece, captured

    def undo_probe(self, from_pos, to_pos, piece, captured):
        """Exact inverse of `probe_move`; see its docstring."""
        fx, fy = from_pos
        tx, ty = to_pos

        self.board[fy][fx] = piece
        self.board[ty][tx] = captured
        if piece is not None:
            piece.x, piece.y = fx, fy
        if captured is not None:
            captured.x, captured.y = tx, ty

    def move(self, from_pos, to_pos):
        fx, fy = from_pos
        tx, ty = to_pos

        piece = self.board[fy][fx]
        captured = self.board[ty][tx]

        # Update Zobrist hash before mutating piece coordinates.
        if piece is not None:
            self.zobrist_hash ^= Zobrist.PIECE_KEYS[
                (piece.color, piece.type, fx, fy)
            ]

        if captured is not None:
            self.zobrist_hash ^= Zobrist.PIECE_KEYS[
                (captured.color, captured.type, tx, ty)
            ]

        self.zobrist_hash ^= Zobrist.SIDE_KEY

        self.board[ty][tx] = piece
        self.board[fy][fx] = None

        if piece is not None:
            piece.x, piece.y = tx, ty
            self.zobrist_hash ^= Zobrist.PIECE_KEYS[
                (piece.color, piece.type, tx, ty)
            ]

        self.history.append((from_pos, to_pos, piece, captured))
        self.current_player = self.opponent(self.current_player)
        self.position_history.append(self.zobrist_hash)

    def undo(self):
        if not self.history:
            return

        from_pos, to_pos, piece, captured = self.history.pop()

        fx, fy = from_pos
        tx, ty = to_pos

        # Reverse the exact hash operations performed by move().
        if piece is not None:
            self.zobrist_hash ^= Zobrist.PIECE_KEYS[
                (piece.color, piece.type, tx, ty)
            ]

        if captured is not None:
            self.zobrist_hash ^= Zobrist.PIECE_KEYS[
                (captured.color, captured.type, tx, ty)
            ]

        self.zobrist_hash ^= Zobrist.SIDE_KEY

        self.board[fy][fx] = piece
        self.board[ty][tx] = captured

        if piece is not None:
            piece.x, piece.y = fx, fy
            self.zobrist_hash ^= Zobrist.PIECE_KEYS[
                (piece.color, piece.type, fx, fy)
            ]

        self.current_player = self.opponent(self.current_player)
        self.position_history.pop()

    def repetition_count(self, position_hash=None):
        """Return how many times a position occurred on the current path."""
        if position_hash is None:
            position_hash = self.zobrist_hash
        return sum(h == position_hash for h in self.position_history)

    def is_repetition(self, position_hash=None, minimum=3):
        """Return True when the exact position occurred at least ``minimum`` times."""
        if minimum < 1:
            raise ValueError("minimum must be at least 1")
        return self.repetition_count(position_hash) >= minimum

    def __str__(self):
        lines = []
        for row in reversed(self.board):
            lines.append(
                " ".join(
                    str(p) if p else ".."
                    for p in row
                )
            )
        return "\n".join(lines)
