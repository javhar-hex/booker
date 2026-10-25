from __future__ import annotations

import dataclasses as dc

from booker.core.model.team import Team


@dc.dataclass(frozen=True, slots=True, order=True)
class Pairing:
    """
    A pair of two distinct teams, representing a match that has been played or will be
    played. Canonical form with `low < high`.
    """

    low: Team
    high: Team

    def __post_init__(self) -> None:
        if not self.low < self.high:
            raise ValueError(f"need low < high, got {self.low} and {self.high}")

    @classmethod
    def of(cls, a: Team, b: Team) -> Pairing:
        return cls(low=min(a, b), high=max(a, b))

    def involves(self, team: Team) -> bool:
        return team in (self.low, self.high)

    def opponent(self, team: Team) -> Team:
        if not self.involves(team):
            raise ValueError(f"{team} is not in {self}")
        return self.high if team == self.low else self.low
