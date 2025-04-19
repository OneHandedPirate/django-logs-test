from collections import defaultdict
from pathlib import Path


def int_defaultdict() -> defaultdict[str, int]:
    return defaultdict(int)


def check_logfiles(logfiles: list[str]) -> bool:
    if not logfiles:
        return False
    for file in logfiles:
        if not Path(file).exists() or not Path(file).is_file():
            return False

    return True
