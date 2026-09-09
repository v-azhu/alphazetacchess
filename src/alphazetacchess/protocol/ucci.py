"""Minimal UCCI protocol adapter for AlphaZetaChess.

The adapter intentionally keeps protocol concerns outside the search engine.
UCCI positions are represented by a FEN plus the move list from that position,
which also lets GameRecord reconstruct exact-position repetition history.
"""

from threading import Event, Lock, Thread

from ..core.board import Board
from ..core.fen import board_from_fen, board_to_fen
from ..core.game_record import GameRecord
from ..core.rule import Rule
from ..engine.search import SearchCancelled, SearchEngine


class UCCIError(ValueError):
    """Raised when a UCCI command is malformed or cannot be applied."""


class UCCIEngine:
    """UCCI command processor with an asynchronous search worker.

    ``handle_line`` remains a line-oriented command processor, while ``go``
    starts a worker thread so that the protocol loop can receive ``stop``.
    The worker searches a private board snapshot and publishes exactly one
    final ``bestmove`` or ``nobestmove`` response.
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
        self._search_thread = None
        self._search_stop_event = None
        self._search_lock = Lock()
        self._pending_responses = []

    def handle_line(self, line):
        line = line.strip()
        if not line:
            return self._drain_responses()

        parts = line.split()
        command = parts[0].lower()

        if command == "ucci":
            return self._drain_responses() + [
                f"id name {self.NAME}",
                f"id author {self.AUTHOR}",
                "option usemillisec type check default false",
                "option newgame type button",
                "ucciok",
            ]
        if command == "isready":
            return self._drain_responses() + ["readyok"]
        if command == "debug":
            if len(parts) != 2 or parts[1].lower() not in {"on", "off"}:
                raise UCCIError("debug expects 'on' or 'off'")
            self.debug = parts[1].lower() == "on"
            return self._drain_responses()
        if command == "setoption":
            self._handle_setoption(parts[1:])
            return self._drain_responses()
        if command == "position":
            self._handle_position(parts[1:])
            return self._drain_responses()
        if command == "go":
            responses = self._drain_responses()
            self._handle_go(parts[1:])
            return responses + self._drain_responses()
        if command == "stop":
            return self._drain_responses() + self._handle_stop()
        if command == "quit":
            self._handle_stop()
            self.quit_requested = True
            return self._drain_responses()
        if command == "bye":
            self._handle_stop()
            self.quit_requested = True
            return self._drain_responses()

        raise UCCIError(f"Unknown UCCI command: {parts[0]}")

    def _handle_setoption(self, args):
        if len(args) < 2 or args[0].lower() != "name":
            raise UCCIError("setoption requires 'name'")

        name = args[1].lower()
        if name == "newgame":
            self._ensure_not_searching()
            self._reset_position()
            return
        if name == "usemillisec":
            # Accepted for protocol compatibility. Search currently only
            # supports depth-based limits, so the value is intentionally not
            # used yet.
            return
        raise UCCIError(f"Unsupported UCCI option: {args[1]}")

    def _handle_position(self, args):
        self._ensure_not_searching()

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
        self._ensure_not_searching()

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
            self._publish_response("nobestmove")
            return

        legal_moves = Rule.generate_legal_moves(
            self.board, self.board.current_player
        )
        if not legal_moves:
            self._publish_response("nobestmove")
            return

        self.search_engine.depth = depth
        search_fen = board_to_fen(self.board)
        stop_event = Event()

        with self._search_lock:
            self._searching = True
            self._search_stop_event = stop_event
            self._search_thread = Thread(
                target=self._search_worker,
                args=(search_fen, stop_event),
                name="AlphaZetaChess-search",
                daemon=True,
            )
            self._search_thread.start()

    def _search_worker(self, search_fen, stop_event):
        """Search a private position snapshot and publish one final response."""
        try:
            board = board_from_fen(search_fen)
            color = board.current_player
            result = self.search_engine.choose_move(
                board, color, stop_event=stop_event
            )

            if result.best_move is None:
                response = "nobestmove"
            else:
                move = GameRecord.move_to_iccs(result.best_move)
                info = f"info depth {result.depth} nodes {result.nodes_evaluated} pv {move}"
                response = f"{info}\nbestmove {move}"
        except SearchCancelled:
            response = "nobestmove"
        except Exception as exc:
            response = f"info string search error {exc}\nnobestmove"
        finally:
            self._publish_response(response)
            with self._search_lock:
                self._searching = False
                self._search_stop_event = None
                self._search_thread = None

    def _handle_stop(self):
        with self._search_lock:
            thread = self._search_thread
            stop_event = self._search_stop_event

        if thread is None:
            return []

        stop_event.set()
        thread.join()
        return self._drain_responses()

    def _publish_response(self, response):
        with self._search_lock:
            self._pending_responses.extend(response.splitlines())

    def _drain_responses(self):
        with self._search_lock:
            responses = list(self._pending_responses)
            self._pending_responses.clear()
        return responses

    def _ensure_not_searching(self):
        with self._search_lock:
            if self._searching:
                raise UCCIError("Search is in progress; send 'stop' first")

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
