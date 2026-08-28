from .piece import PieceType
from .move import Move


class MoveGenerator:
    """
    Generate pseudo-legal moves.

    Core v0.2:
    - Rook
    - Horse

    Future:
    - Cannon
    - Elephant
    - Advisor
    - King
    - Pawn
    - Check validation
    """

    def generate_moves(self, board, color):
        moves = []

        for y in range(board.HEIGHT):
            for x in range(board.WIDTH):
                piece = board.get(x, y)

                if piece is None:
                    continue

                if piece.color != color:
                    continue

                moves.extend(
                    self.generate_piece_moves(board, piece)
                )

        return moves


    def generate_piece_moves(self, board, piece):

        if piece.type == PieceType.ROOK:
            return self._rook_moves(board, piece)

        if piece.type == PieceType.HORSE:
            return self._horse_moves(board, piece)

        return []


    def _rook_moves(self, board, piece):

        moves = []

        directions = [
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
        ]

        for dx, dy in directions:

            x = piece.x
            y = piece.y

            while True:

                x += dx
                y += dy

                if not (
                    0 <= x < board.WIDTH
                    and
                    0 <= y < board.HEIGHT
                ):
                    break

                target = board.get(x, y)

                if target is None:

                    moves.append(
                        Move(
                            piece.position(),
                            (x, y)
                        )
                    )

                else:

                    if target.color != piece.color:
                        moves.append(
                            Move(
                                piece.position(),
                                (x, y)
                            )
                        )

                    break

        return moves


    def _horse_moves(self, board, piece):

        moves = []

        # 目标位置, 马腿位置
        candidates = [
            ((1, 2), (0, 1)),
            ((-1, 2), (0, 1)),
            ((1, -2), (0, -1)),
            ((-1, -2), (0, -1)),

            ((2, 1), (1, 0)),
            ((2, -1), (1, 0)),
            ((-2, 1), (-1, 0)),
            ((-2, -1), (-1, 0)),
        ]


        for target_offset, leg_offset in candidates:

            # 检查马腿
            leg_x = piece.x + leg_offset[0]
            leg_y = piece.y + leg_offset[1]


            if not (
                0 <= leg_x < board.WIDTH
                and
                0 <= leg_y < board.HEIGHT
            ):
                continue


            if board.get(leg_x, leg_y) is not None:
                continue


            # 检查目标位置
            x = piece.x + target_offset[0]
            y = piece.y + target_offset[1]


            if not (
                0 <= x < board.WIDTH
                and
                0 <= y < board.HEIGHT
            ):
                continue


            target = board.get(x, y)


            if (
                target is None
                or
                target.color != piece.color
            ):

                moves.append(
                    Move(
                        piece.position(),
                        (x, y)
                    )
                )


        return moves