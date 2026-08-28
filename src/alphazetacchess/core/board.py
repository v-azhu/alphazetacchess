from .piece import Piece, PieceType, Color


class Board:
    WIDTH = 9
    HEIGHT = 10

    def __init__(self):
        self.board = [
            [None for _ in range(self.WIDTH)]
            for _ in range(self.HEIGHT)
        ]
        self.history = []
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

    def move(self, from_pos, to_pos):
        fx, fy = from_pos
        tx, ty = to_pos

        piece = self.board[fy][fx]
        captured = self.board[ty][tx]

        self.board[ty][tx] = piece
        self.board[fy][fx] = None

        self.history.append((from_pos, to_pos, piece, captured))

    def undo(self):
        if not self.history:
            return

        from_pos, to_pos, piece, captured = self.history.pop()

        fx, fy = from_pos
        tx, ty = to_pos

        self.board[fy][fx] = piece
        self.board[ty][tx] = captured

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
