"""Console entry point for the AlphaZetaChess UCCI engine."""

import sys

from alphazetacchess.protocol.ucci import run_ucci


if __name__ == "__main__":
    run_ucci(sys.stdin, sys.stdout)
