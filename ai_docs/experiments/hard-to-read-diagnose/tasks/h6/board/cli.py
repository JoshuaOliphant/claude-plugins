import json
import sys

from .entries import Entry
from .ranking import standings


def main(argv=None):
    raw = json.load(open((argv or sys.argv)[1]))
    entries = [Entry(**r) for r in raw]
    for rank, player, score in standings(entries):
        print(f"{rank:>2}. {player:<10} {score}")


if __name__ == "__main__":
    main()
