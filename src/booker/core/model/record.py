from __future__ import annotations

import dataclasses as dc

from booker.core.model.invariants import CHAMPION_WINS, ELIMINATION_LOSSES


@dc.dataclass(frozen=True, slots=True)
class Record:
    """
    A team's wins and losses so far. A team with `ELIMINATION_LOSSES` is eliminated; a
    team with `CHAMPION_WINS` wins is the champion.
    """

    wins: int
    losses: int

    def __post_init__(self) -> None:
        if not 0 <= self.wins <= CHAMPION_WINS:
            raise ValueError(f"wins must be in [0, {CHAMPION_WINS}], got {self.wins}")
        if not 0 <= self.losses <= ELIMINATION_LOSSES:
            raise ValueError(
                f"losses must be in [0, {ELIMINATION_LOSSES}], got {self.losses}"
            )

    @classmethod
    def fresh(cls) -> Record:
        return cls(wins=0, losses=0)

    def __str__(self) -> str:
        return f"{self.wins}-{self.losses}"

    @property
    def played(self) -> int:
        return self.wins + self.losses

    @property
    def is_unbeaten(self) -> bool:
        return self.losses == 0

    @property
    def is_eliminated(self) -> bool:
        return self.losses == ELIMINATION_LOSSES

    def plus(self, wins: int, losses: int) -> Record:
        if wins < 0 or losses < 0:
            raise ValueError(f"cannot take back results: {wins} wins, {losses} losses")
        if self.is_eliminated and wins + losses:
            raise ValueError(f"an eliminated team ({self}) plays no more matches")
        return Record(wins=self.wins + wins, losses=self.losses + losses)
