class Move:
    def __init__(self, from_pos, to_pos):
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.moved_piece = None
        self.captured_piece = None

    def __repr__(self):
        return f"{self.from_pos}->{self.to_pos}"
