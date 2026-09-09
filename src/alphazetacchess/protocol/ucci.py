"""Minimal UCCI protocol adapter for AlphaZetaChess.

The adapter intentionally keeps protocol concerns outside the search engine.
UCCI positions are represented by a FEN plus the move list from that position,
which also lets GameRecord reconstruct exact-position repetition history.
"""

from ..core.board import Board
from ..core.fen import board_to_fen
from ..core.game_record import GameRecord
from ..core.rule import Rule
from ..engine.search import SearchEngine


class UCCIError(ValueError):
    """Raised when a UCCI command is malformed or cannot be applied."""


class UCCIEngine:
    """Synchronous UCCI command processor.

    ``handle_line`` returns zero or more protocol lines. Search is currently
    synchronous; asynchronous stop/time-control support belongs to the next
    protocol iteration.
    """

    NAME = "AlphaZetaChess"
    AUTHOR = "v-azhu"

    def __init__(self, search_engine=None):
        self.search_engine = search_engine or SearchEngine(depth=3)
        self.board = Board()
        self.record = GameRecord.from_board(self.board)
        self.debug = False
        self.quit_requested = False
        self._searching = False

    def handle_line(self, line):
        line = line.strip()
        if not line:
            return []

        parts = line.split()
        command = parts[0].lower()

        if command == "ucci":
            return [
                f"id name {self.NAME}",
                f"id author {self.AUTHOR}",
                "option usemillisec type check default false",
                "option newgame type button",
                "ucciok",
            ]
        if command == "isready":
            return ["readyok"]
        if command == "debug":
            if len(parts) != 2 or parts[1].lower() not in {"on", "off"}:
                raise UCCIError("debug expects 'on' or 'off'")
            self.debug = parts[1].lower() == "on"
            return []
        if command == "setoption":
            self._handle_setoption(parts[1:])
            return []
        if command == "position":
            self._handle_position(parts[1:])
            return []
        if command == "go":
            return self._handle_go(parts[1:])
        if command == "stop":
            # Search is synchronous, so there is no running worker to cancel.
            # If a future asynchronous implementation is active, this branch
            # is the place where the cancellation event will be handled.
            return ["nobestmove"] if self._searching else []
        if command == "quit":
            self.quit_requested = True
            return []
        if command == "bye":
            self.quit_requested = True
            return []

        raise UCCIError(f"Unknown UCCI command: {parts[0]}")

    def _handle_setoption(self, args):
        if len(args) < 2 or args[0].lower() != "name":
            raise UCCIError("setoption requires 'name'")

        name = args[1].lower()
        if name == "newgame":
            self._reset_position()
            return
        if name == "usemillisec":
            # Accepted for protocol compatibility. Search currently only
            # supports depth-based limits, so the value is intentionally not
            # used yet.
            return
        raise UCCIError(f"Unsupported UCCI option: {args[1]}")

    def _handle_position(self, args):
        if not args or args[0].lower() != "fen":
            raise UCCIError("UCCI requires 'position fen <fen> [moves ...]'")

        try:
            moves_index = next(
                index for index, token in enumerate(args[1:], start=1)
                if token.lower() == "moves"
            )
        except StopIteration:
            moves_index = len(args)

        fen_fields = args[1:moves_index]
        if len(fen_fields) != 6:
            raise UCCIError("FEN must contain exactly six fields")

        fen = " ".join(fen_fields)
        move_texts = args[moves_index + 1:] if moves_index < len(args) else []

        try:
            record = GameRecord.from_moves(fen, move_texts)
            board = record.replay()
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise UCCIError(f"Invalid position: {exc}") from exc

        self.record = record
        self.board = board

    def _handle_go(self, args):
        depth = self.search_engine.depth
        if args:
            if len(args) != 2 or args[0].lower() != "depth":
                raise UCCIError("Current UCCI implementation supports only 'go depth N'")
            try:
                depth = int(args[1])
            except ValueError as exc:
                raise UCCIError("Search depth must be an integer") from exc
            if depth < 0:
                raise UCCIError("Search depth cannot be negative")

        if depth == 0:
            return ["nobestmove"]

        legal_moves = Rule.generate_legal_moves(
            self.board, self.board.current_player
        )
        if not legal_moves:
            return ["nobestmove"]

        self.search_engine.depth = depth
        self._searching = True
        try:
            result = self.search_engine.choose_move(
                self.board, self.board.current_player
            )
        finally:
            self._searching = False

        if result.best_move is None:
            return ["nobestmove"]

        move = GameRecord.move_to_iccs(result.best_move)
        info = f"info depth {result.depth} nodes {result.nodes_evaluated} pv {move}"
        return [info, f"bestmove {move}"]

    def _reset_position(self):
        self.board = Board()
        self.record = GameRecord.from_board(self.board)

    def current_fen(self):
        """Return the engine's current position as FEN."""
        return board_to_fen(self.board)


def run_ucci(input_stream, output_stream):
    """Run a line-oriented UCCI loop over file-like streams."""
    engine = UCCIEngine()
    for line in input_stream:
        try:
            responses = engine.handle_line(line)
        except UCCIError as exc:
            responses = [f"info string error {exc}"]

        for response in responses:
            output_stream.write(response + "\n")
            output_stream.flush()

        if engine.quit_requested:
            break
