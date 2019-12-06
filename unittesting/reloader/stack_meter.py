class StackMeter:
    """Reentrant context manager counting the reentrancy depth."""

    def __init__(self, depth=0):
        super().__init__()
        self.depth = depth

    def __enter__(self):  # noqa
        depth = self.depth
        self.depth += 1
        return depth

    def __exit__(self, *exc_info):  # noqa
        self.depth -= 1
