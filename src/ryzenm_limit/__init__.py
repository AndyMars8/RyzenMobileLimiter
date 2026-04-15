import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
import daemon
from parse_args import ParseArgs


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "start":
            daemon.start()
            return
    ParseArgs()
