from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    player: str
    score: int
    round: int
