"""
AlphaZetaChess - playable CLI (V0.1-V0.3.5).

A Human (RED) vs SearchEngine AI (BLACK) command-line game, built on
top of the Core layer (Board / MoveGenerator / Rule) and the Engine
layer (Negamax + Alpha-Beta + PVS + Quiescence Search with iterative
deepening, root/TT move ordering, and a Zobrist-hashed transposition
table).
"""

import os
import sys

# Make the "alphazetacchess" package importable when this file is run
# directly as `python src/main.py`, regardless of the current working
# directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine


HUMAN_COLOR = Color.RED
AI_COLOR = Color.BLACK

# Measured on 2026-08-30 (see docs/v0.3.4.md for the full table):
#   depth=2: ~0.5-5s per move (Quiescence Search adds ~75-85% time on
#            tactically active positions; roughly free to slightly
#            faster on quiet ones)
#   depth=3: ~9-31s per move -- much more variable than before V0.3.4,
#            since Quiescence Search's cost depends heavily on how many
#            open capture lines exist at the horizon (opening positions
#            are the expensive case)
#   depth=4: still >55s from the opening position, not yet practical
# Kept at 2 by default for a snappy CLI experience; bump to 3 for a
# noticeably stronger (but slower and less predictably-timed) opponent.
AI_SEARCH_DEPTH = 2


def print_board(board):
    print("    " + "  ".join(str(x) for x in range(Board.WIDTH)))
    for y in range(Board.HEIGHT - 1, -1, -1):
        row_cells = []
        for x in range(Board.WIDTH):
            piece = board.get(x, y)
            row_cells.append(str(piece) if piece else "..")
        print(f"{y:2d}  " + "  ".join(row_cells))
    print()


def color_name(color):
    return "红方 RED" if color == Color.RED else "黑方 BLACK"


def parse_human_move(text):
    parts = text.split()
    if len(parts) != 4:
        return None
    try:
        fx, fy, tx, ty = (int(p) for p in parts)
    except ValueError:
        return None
    return (fx, fy), (tx, ty)


def get_human_move(board):
    legal_moves = Rule.generate_legal_moves(board, HUMAN_COLOR)

    while True:
        text = input(
            "请输入走法 (格式: 起点x 起点y 终点x 终点y, 例如 0 0 0 1), "
            "输入 quit 退出: "
        ).strip()

        if text.lower() in ("quit", "exit"):
            return None

        parsed = parse_human_move(text)
        if parsed is None:
            print("输入格式不正确，请重新输入。")
            continue

        from_pos, to_pos = parsed

        if not Board.in_bounds(*from_pos):
            print("起点坐标超出棋盘范围，请重新输入。")
            continue

        piece = board.get(*from_pos)
        if piece is None or piece.color != HUMAN_COLOR:
            print("起点没有你的棋子，请重新输入。")
            continue

        match = next(
            (
                m for m in legal_moves
                if m.from_pos == from_pos and m.to_pos == to_pos
            ),
            None,
        )

        if match is None:
            print("这不是一个合法的走法，请重新输入。")
            continue

        return match


def describe_move(move):
    text = f"{move.from_pos} -> {move.to_pos}"
    if move.captured_piece is not None:
        text += f" (吃子 capture: {move.captured_piece})"
    return text


def describe_search_result(result):
    """
    Makes the AI's decision explainable (V0.2 acceptance criterion):
    shows the move it picked, the evaluation score it expects from
    that move (positive = good for the AI), and how many positions it
    had to look at to decide.
    """
    return (
        f"{describe_move(result.best_move)} "
        f"| 评估分数 score={result.score} "
        f"| 搜索深度 depth={result.depth} "
        f"| 计算节点 nodes={result.nodes_evaluated}"
    )


def main():
    print("AlphaZetaChess")
    print(f"Human (RED) vs SearchEngine AI (BLACK, depth={AI_SEARCH_DEPTH})")
    print()

    board = Board()
    ai_engine = SearchEngine(depth=AI_SEARCH_DEPTH)

    while True:
        print_board(board)

        current = board.current_player

        if Rule.is_checkmate(board, current):
            winner = Board.opponent(current)
            print(f"{color_name(current)} 被将死 (checkmate)，{color_name(winner)} 获胜！")
            break

        if Rule.is_stalemate(board, current):
            winner = Board.opponent(current)
            print(f"{color_name(current)} 无子可走 (stalemate/困毙)，{color_name(winner)} 获胜！")
            break

        if Rule.is_in_check(board, current):
            print(f"{color_name(current)} 正被将军 (check)！")

        if current == HUMAN_COLOR:
            move = get_human_move(board)
            if move is None:
                print("已退出游戏。")
                break
        else:
            print(f"{color_name(AI_COLOR)} 正在思考...")
            result = ai_engine.choose_move(board, AI_COLOR)
            move = result.best_move
            print(f"{color_name(AI_COLOR)} 走: {describe_search_result(result)}")

        board.move(move.from_pos, move.to_pos)


if __name__ == "__main__":
    main()
