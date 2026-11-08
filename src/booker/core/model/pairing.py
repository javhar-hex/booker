from __future__ import annotations

import dataclasses as dc

from booker.core.model.team import Team


@dc.dataclass(frozen=True, slots=True, order=True)
class Pairing:
    """
    A pair of two distinct teams, representing a match that has been played or will be
    played. Canonical form with `lhs < rhs`.
    """

    lhs: Team
    rhs: Team

    def __post_init__(self) -> None:
        if not self.lhs < self.rhs:
            raise ValueError(f"need lhs < rhs, got {self.lhs} and {self.rhs}")

    @classmethod
    def of(cls, team_lhs: Team, team_rhs: Team) -> Pairing:
        return cls(lhs=min(team_lhs, team_rhs), rhs=max(team_lhs, team_rhs))

    def involves(self, team: Team) -> bool:
        return team in (self.lhs, self.rhs)

    def opponent(self, team: Team) -> Team:
        if not self.involves(team):
            raise ValueError(f"{team} is not in {self}")
        return self.rhs if team == self.lhs else self.lhs
