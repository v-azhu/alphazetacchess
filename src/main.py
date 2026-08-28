"""
AlphaZetaChess - v0.1 playable milestone.

A minimal Human (RED) vs Random AI (BLACK) command-line game, built on
top of the Core layer (Board / MoveGenerator / Rule).
"""

import os
import random
import sys

# Make the "alphazetacchess" package importable when this file is run
# directly as `python src/main.py`, regardless of the current working
# directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.rule import Rule


HUMAN_COLOR = Color.RED
AI_COLOR = Color.BLACK


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


def get_ai_move(board):
    legal_moves = Rule.generate_legal_moves(board, AI_COLOR)
    return random.choice(legal_moves)


def describe_move(move):
    text = f"{move.from_pos} -> {move.to_pos}"
    if move.captured_piece is not None:
        text += f" (吃子 capture: {move.captured_piece})"
    return text


def main():
    print("AlphaZetaChess")
    print("Human (RED) vs Random AI (BLACK)")
    print()

    board = Board()

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
            move = get_ai_move(board)
            print(f"{color_name(AI_COLOR)} 走: {describe_move(move)}")

        board.move(move.from_pos, move.to_pos)


if __name__ == "__main__":
    main()
