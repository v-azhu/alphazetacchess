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
        self.history = []
        self.current_player = Color.RED
        self.setup()
        self.zobrist_hash = Zobrist.board_hash(self)

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
