"""Minimal UCI engine fixture for the tactics root-labeling adapter."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.core.rule import Rule


fen = None
multipv = 1
for line in sys.stdin:
    command = line.strip()
    if command == "uci":
        print("id name FakeMultiPV", flush=True)
        print("uciok", flush=True)
    elif command == "isready":
        print("readyok", flush=True)
    elif command.startswith("setoption name MultiPV value "):
        multipv = int(command.rsplit(" ", 1)[1])
    elif command.startswith("position fen "):
        fen = command[len("position fen "):]
    elif command.startswith("go depth "):
        tokens = command.split()
        depth = int(tokens[2])
        board = board_from_fen(fen)
        legal = [
            GameRecord.move_to_iccs(move)
            for move in Rule.generate_legal_moves(board, board.current_player)
        ]
        if "searchmoves" in tokens:
            requested = tokens[tokens.index("searchmoves") + 1:]
            legal = [move for move in legal if move in requested]
        legal = legal[:multipv]
        for index, move in enumerate(legal, start=1):
            print(
                f"info depth {depth} multipv {index} score cp {100 - index} pv {move}",
                flush=True,
            )
        print(f"bestmove {legal[0] if legal else '0000'}", flush=True)
    elif command == "quit":
        break
