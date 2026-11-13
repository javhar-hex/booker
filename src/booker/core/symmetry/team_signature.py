"""What an isomorphism cannot change about one team."""

from __future__ import annotations

import dataclasses as dc

from booker.core.model.state import State
from booker.core.model.team import Team


@dc.dataclass(frozen=True, slots=True, order=True)
class TeamSignature:
    "A team's record, and the number of teams it has met."

    wins: int
    losses: int
    degree: int

    @classmethod
    def of(cls, state: State, team: Team) -> TeamSignature:
        record = state.record(team)
        degree = sum(pairing.involves(team) for pairing in state.past_pairings)
        return cls(wins=record.wins, losses=record.losses, degree=degree)
