from .piece import Piece, PieceType, Color


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
        self.history = []
        self.current_player = Color.RED
        self.setup()

    def setup(self):
        # Red side
        self._place_back_rank(0, Color.RED)
        self._place_cannon(2, Color.RED)
        for x in [0, 2, 4, 6, 8]:
            self._place(Piece(PieceType.PAWN, Color.RED, x, 3))

        # Black side
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

    # ------------------------------------------------------------------
    # Geometry helpers
    #
    # These are shared between MoveGenerator (move pattern restrictions)
    # and Rule (check / checkmate detection), so they live on Board
    # rather than being duplicated in both places.
    # ------------------------------------------------------------------

    @staticmethod
    def in_bounds(x, y):
        return 0 <= x < Board.WIDTH and 0 <= y < Board.HEIGHT

    @staticmethod
    def in_palace(x, y, color):
        """
        Advisors and Kings may never leave the 3x3 palace.
        """
        if x not in Board.PALACE_X:
            return False
        if color == Color.RED:
            return y in Board.RED_PALACE_Y
        return y in Board.BLACK_PALACE_Y

    @staticmethod
    def has_crossed_river(y, color):
        """
        Used by Elephants (may never cross) and Pawns (gain sideways
        movement after crossing).
        """
        if color == Color.RED:
            return y >= 5
        return y <= 4

    @staticmethod
    def opponent(color):
        return Color.BLACK if color == Color.RED else Color.RED

    def find_king(self, color):
        for row in self.board:
            for piece in row:
                if (
                    piece is not None
                    and piece.type == PieceType.KING
                    and piece.color == color
                ):
                    return piece
        return None

    def kings_facing(self):
        """
        "Flying general" rule: the two generals may never face each
        other directly on the same file with nothing in between. This
        is checked separately from normal attack patterns because a
        King's own movement never "attacks" along the whole file.
        """
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

    # ------------------------------------------------------------------
    # Move execution
    # ------------------------------------------------------------------

    def move(self, from_pos, to_pos):
        fx, fy = from_pos
        tx, ty = to_pos

        piece = self.board[fy][fx]
        captured = self.board[ty][tx]

        self.board[ty][tx] = piece
        self.board[fy][fx] = None

        if piece is not None:
            piece.x, piece.y = tx, ty

        self.history.append((from_pos, to_pos, piece, captured))
        self.current_player = self.opponent(self.current_player)

    def undo(self):
        if not self.history:
            return

        from_pos, to_pos, piece, captured = self.history.pop()

        fx, fy = from_pos
        tx, ty = to_pos

        self.board[fy][fx] = piece
        self.board[ty][tx] = captured

        if piece is not None:
            piece.x, piece.y = fx, fy

        self.current_player = self.opponent(self.current_player)

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
