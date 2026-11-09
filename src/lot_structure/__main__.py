import sys
from pathlib import Path

from lot_structure.gui import start


def main() -> int:
    return start(Path(__file__).resolve().parents[2])


if __name__ == '__main__':
    sys.exit(main())
