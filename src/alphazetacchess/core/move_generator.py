from .piece import PieceType, Color
from .move import Move
from .board import Board


class MoveGenerator:
    """
    Generate pseudo-legal moves for all seven Chinese Chess piece types.

    "Pseudo-legal" means the move follows the movement pattern of the
    piece -- including special restrictions such as the horse leg,
    the cannon screen, the elephant eye, the river, and the palace
    boundaries -- but does NOT check whether making the move would
    leave the mover's own general in check. That final legality
    filter is the responsibility of the Rule engine.
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
        handlers = {
            PieceType.ROOK: self._rook_moves,
            PieceType.HORSE: self._horse_moves,
            PieceType.CANNON: self._cannon_moves,
            PieceType.ELEPHANT: self._elephant_moves,
            PieceType.ADVISOR: self._advisor_moves,
            PieceType.KING: self._king_moves,
            PieceType.PAWN: self._pawn_moves,
        }

        handler = handlers.get(piece.type)

        if handler is None:
            return []

        return handler(board, piece)

    def _make_move(self, piece, to_pos, target):
        move = Move(piece.position(), to_pos)
        move.moved_piece = piece
        move.captured_piece = target
        return move

    # ------------------------------------------------------------------
    # Rook (车): moves any distance orthogonally, blocked by pieces.
    # ------------------------------------------------------------------
    def _rook_moves(self, board, piece):
        moves = []
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        for dx, dy in directions:
            x, y = piece.x, piece.y

            while True:
                x += dx
                y += dy

                if not Board.in_bounds(x, y):
                    break

                target = board.get(x, y)

                if target is None:
                    moves.append(self._make_move(piece, (x, y), None))
                else:
                    if target.color != piece.color:
                        moves.append(self._make_move(piece, (x, y), target))
                    break

        return moves

    # ------------------------------------------------------------------
    # Cannon (炮): moves like a Rook when not capturing. To capture, it
    # must jump over exactly one piece (the "screen") in that direction.
    # ------------------------------------------------------------------
    def _cannon_moves(self, board, piece):
        moves = []
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        for dx, dy in directions:
            x, y = piece.x, piece.y
            screen_found = False

            while True:
                x += dx
                y += dy

                if not Board.in_bounds(x, y):
                    break

                target = board.get(x, y)

                if not screen_found:
                    if target is None:
                        moves.append(self._make_move(piece, (x, y), None))
                    else:
                        # First piece encountered becomes the screen.
                        # The cannon cannot land on it directly.
                        screen_found = True
                else:
                    if target is None:
                        continue
                    if target.color != piece.color:
                        moves.append(self._make_move(piece, (x, y), target))
                    # Whether captured or blocked by a friendly piece,
                    # the cannon cannot see past the piece after the screen.
                    break

        return moves

    # ------------------------------------------------------------------
    # Horse (马): moves 1 orthogonal + 1 diagonal, blocked by the piece
    # directly adjacent in the orthogonal direction ("horse leg" / 蹩腿).
    # ------------------------------------------------------------------
    def _horse_moves(self, board, piece):
        moves = []

        # (target offset, leg/blocking offset)
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
            leg_x = piece.x + leg_offset[0]
            leg_y = piece.y + leg_offset[1]

            if not Board.in_bounds(leg_x, leg_y):
                continue

            if board.get(leg_x, leg_y) is not None:
                continue

            x = piece.x + target_offset[0]
            y = piece.y + target_offset[1]

            if not Board.in_bounds(x, y):
                continue

            target = board.get(x, y)

            if target is None or target.color != piece.color:
                moves.append(self._make_move(piece, (x, y), target))

        return moves

    # ------------------------------------------------------------------
    # Elephant (象/相): moves exactly 2 squares diagonally, blocked if
    # the midpoint ("elephant eye" / 塞象眼) is occupied. May never
    # cross the river.
    # ------------------------------------------------------------------
    def _elephant_moves(self, board, piece):
        moves = []
        offsets = [(2, 2), (2, -2), (-2, 2), (-2, -2)]

        for dx, dy in offsets:
            x = piece.x + dx
            y = piece.y + dy

            if not Board.in_bounds(x, y):
                continue

            if Board.has_crossed_river(y, piece.color):
                continue

            eye_x = piece.x + dx // 2
            eye_y = piece.y + dy // 2

            if board.get(eye_x, eye_y) is not None:
                continue

            target = board.get(x, y)

            if target is None or target.color != piece.color:
                moves.append(self._make_move(piece, (x, y), target))

        return moves

    # ------------------------------------------------------------------
    # Advisor (士/仕): moves 1 square diagonally, confined to the palace.
    # ------------------------------------------------------------------
    def _advisor_moves(self, board, piece):
        moves = []
        offsets = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

        for dx, dy in offsets:
            x = piece.x + dx
            y = piece.y + dy

            if not Board.in_palace(x, y, piece.color):
                continue

            target = board.get(x, y)

            if target is None or target.color != piece.color:
                moves.append(self._make_move(piece, (x, y), target))

        return moves

    # ------------------------------------------------------------------
    # King (将/帅): moves 1 square orthogonally, confined to the palace.
    # The "flying general" rule is enforced separately by Rule, since it
    # is a position-level restriction rather than a normal move pattern.
    # ------------------------------------------------------------------
    def _king_moves(self, board, piece):
        moves = []
        offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        for dx, dy in offsets:
            x = piece.x + dx
            y = piece.y + dy

            if not Board.in_palace(x, y, piece.color):
                continue

            target = board.get(x, y)

            if target is None or target.color != piece.color:
                moves.append(self._make_move(piece, (x, y), target))

        return moves

    # ------------------------------------------------------------------
    # Pawn (卒/兵): 1 square forward only before crossing the river.
    # After crossing, gains 1 square sideways, but never moves backward.
    # ------------------------------------------------------------------
    def _pawn_moves(self, board, piece):
        moves = []

        forward = 1 if piece.color == Color.RED else -1
        crossed = Board.has_crossed_river(piece.y, piece.color)

        offsets = [(0, forward)]

        if crossed:
            offsets.append((1, 0))
            offsets.append((-1, 0))

        for dx, dy in offsets:
            x = piece.x + dx
            y = piece.y + dy

            if not Board.in_bounds(x, y):
                continue

            target = board.get(x, y)

            if target is None or target.color != piece.color:
                moves.append(self._make_move(piece, (x, y), target))

        return moves
