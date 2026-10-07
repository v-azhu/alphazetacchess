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

    _ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
    _HORSE_CANDIDATES = (
        ((1, 2), (0, 1)),
        ((-1, 2), (0, 1)),
        ((1, -2), (0, -1)),
        ((-1, -2), (0, -1)),
        ((2, 1), (1, 0)),
        ((2, -1), (1, 0)),
        ((-2, 1), (-1, 0)),
        ((-2, -1), (-1, 0)),
    )
    _ELEPHANT_OFFSETS = ((2, 2), (2, -2), (-2, 2), (-2, -2))
    _ADVISOR_OFFSETS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    _KING_OFFSETS = _ORTHOGONAL
    _PAWN_SIDEWAYS_OFFSETS = ((1, 0), (-1, 0))

    def generate_moves(self, board, color, captures_only=False):
        moves = []
        grid = board.board

        for y in range(board.HEIGHT):
            row = grid[y]
            for x in range(board.WIDTH):
                piece = row[x]

                if piece is None:
                    continue

                if piece.color != color:
                    continue

                moves.extend(self.generate_piece_moves(board, piece, captures_only))

        return moves

    def generate_piece_moves(self, board, piece, captures_only=False):
        if piece.type == PieceType.ROOK:
            return self._rook_moves(board, piece, captures_only)
        if piece.type == PieceType.HORSE:
            return self._horse_moves(board, piece, captures_only)
        if piece.type == PieceType.CANNON:
            return self._cannon_moves(board, piece, captures_only)
        if piece.type == PieceType.ELEPHANT:
            return self._elephant_moves(board, piece, captures_only)
        if piece.type == PieceType.ADVISOR:
            return self._advisor_moves(board, piece, captures_only)
        if piece.type == PieceType.KING:
            return self._king_moves(board, piece, captures_only)
        if piece.type == PieceType.PAWN:
            return self._pawn_moves(board, piece, captures_only)
        return []

    def _make_move(self, piece, to_pos, target):
        move = Move(piece.position(), to_pos)
        move.moved_piece = piece
        move.captured_piece = target
        return move

    # ------------------------------------------------------------------
    # Rook (车): moves any distance orthogonally, blocked by pieces.
    # ------------------------------------------------------------------
    def _rook_moves(self, board, piece, captures_only=False):
        moves = []
        grid = board.board

        for dx, dy in self._ORTHOGONAL:
            x, y = piece.x, piece.y

            while True:
                x += dx
                y += dy

                if not (0 <= x < 9 and 0 <= y < 10):
                    break

                target = grid[y][x]

                if target is None:
                    if not captures_only:
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
    def _cannon_moves(self, board, piece, captures_only=False):
        moves = []
        grid = board.board

        for dx, dy in self._ORTHOGONAL:
            x, y = piece.x, piece.y
            screen_found = False

            while True:
                x += dx
                y += dy

                if not (0 <= x < 9 and 0 <= y < 10):
                    break

                target = grid[y][x]

                if not screen_found:
                    if target is None:
                        if not captures_only:
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
    def _horse_moves(self, board, piece, captures_only=False):
        moves = []
        grid = board.board

        for target_offset, leg_offset in self._HORSE_CANDIDATES:
            leg_x = piece.x + leg_offset[0]
            leg_y = piece.y + leg_offset[1]

            if not (0 <= leg_x < 9 and 0 <= leg_y < 10):
                continue

            if grid[leg_y][leg_x] is not None:
                continue

            x = piece.x + target_offset[0]
            y = piece.y + target_offset[1]

            if not (0 <= x < 9 and 0 <= y < 10):
                continue

            target = grid[y][x]

            if target is not None and target.color != piece.color:
                moves.append(self._make_move(piece, (x, y), target))
            elif target is None and not captures_only:
                moves.append(self._make_move(piece, (x, y), None))

        return moves

    # ------------------------------------------------------------------
    # Elephant (象/相): moves exactly 2 squares diagonally, blocked if
    # the midpoint ("elephant eye" / 塞象眼) is occupied. May never
    # cross the river.
    # ------------------------------------------------------------------
    def _elephant_moves(self, board, piece, captures_only=False):
        moves = []
        grid = board.board

        for dx, dy in self._ELEPHANT_OFFSETS:
            x = piece.x + dx
            y = piece.y + dy

            if not (0 <= x < 9 and 0 <= y < 10):
                continue

            if Board.has_crossed_river(y, piece.color):
                continue

            eye_x = piece.x + dx // 2
            eye_y = piece.y + dy // 2

            if grid[eye_y][eye_x] is not None:
                continue

            target = grid[y][x]

            if target is not None and target.color != piece.color:
                moves.append(self._make_move(piece, (x, y), target))
            elif target is None and not captures_only:
                moves.append(self._make_move(piece, (x, y), None))

        return moves

    # ------------------------------------------------------------------
    # Advisor (士/仕): moves 1 square diagonally, confined to the palace.
    # ------------------------------------------------------------------
    def _advisor_moves(self, board, piece, captures_only=False):
        moves = []
        grid = board.board

        for dx, dy in self._ADVISOR_OFFSETS:
            x = piece.x + dx
            y = piece.y + dy

            if not Board.in_palace(x, y, piece.color):
                continue

            target = grid[y][x]

            if target is not None and target.color != piece.color:
                moves.append(self._make_move(piece, (x, y), target))
            elif target is None and not captures_only:
                moves.append(self._make_move(piece, (x, y), None))

        return moves

    # ------------------------------------------------------------------
    # King (将/帅): moves 1 square orthogonally, confined to the palace.
    # The "flying general" rule is enforced separately by Rule, since it
    # is a position-level restriction rather than a normal move pattern.
    # ------------------------------------------------------------------
    def _king_moves(self, board, piece, captures_only=False):
        moves = []
        grid = board.board

        for dx, dy in self._KING_OFFSETS:
            x = piece.x + dx
            y = piece.y + dy

            if not Board.in_palace(x, y, piece.color):
                continue

            target = grid[y][x]

            if target is not None and target.color != piece.color:
                moves.append(self._make_move(piece, (x, y), target))
            elif target is None and not captures_only:
                moves.append(self._make_move(piece, (x, y), None))

        return moves

    # ------------------------------------------------------------------
    # Pawn (卒/兵): 1 square forward only before crossing the river.
    # After crossing, gains 1 square sideways, but never moves backward.
    # ------------------------------------------------------------------
    def _pawn_moves(self, board, piece, captures_only=False):
        moves = []
        grid = board.board

        forward = 1 if piece.color == Color.RED else -1
        crossed = Board.has_crossed_river(piece.y, piece.color)

        offsets = (
            ((0, forward),) + self._PAWN_SIDEWAYS_OFFSETS
            if crossed
            else ((0, forward),)
        )

        for dx, dy in offsets:
            x = piece.x + dx
            y = piece.y + dy

            if not (0 <= x < 9 and 0 <= y < 10):
                continue

            target = grid[y][x]

            if target is not None and target.color != piece.color:
                moves.append(self._make_move(piece, (x, y), target))
            elif target is None and not captures_only:
                moves.append(self._make_move(piece, (x, y), None))

        return moves
