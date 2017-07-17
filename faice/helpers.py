import sys
import textwrap


def print_user_text(blocks, error=False):
    if error:
        for block in blocks:
            print(textwrap.fill(block), file=sys.stderr)
    else:
        for block in blocks:
            print(textwrap.fill(block))


class Stepper:
    def __init__(self, init=0):
        self.val = init

    def step(self):
        self.val += 1
        return self.val
