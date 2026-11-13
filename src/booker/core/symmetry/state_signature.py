"""A cheap necessary condition for two states to be isomorphic."""

from __future__ import annotations

import dataclasses as dc

from javhar_util.immutables import ZVec

from booker.core.model.state import State
from booker.core.symmetry.team_signature import TeamSignature


@dc.dataclass(frozen=True, slots=True)
class StateSignature:
    """
    The signatures of the teams of a state, sorted. Isomorphic states have equal
    signatures; the converse does not hold, so equal signatures are not an answer, but
    different ones are.
    """

    team_signatures: ZVec[TeamSignature]

    def __post_init__(self) -> None:
        if list(self.team_signatures) != sorted(self.team_signatures):
            raise ValueError("the team signatures are not sorted")

    @classmethod
    def of(cls, state: State) -> StateSignature:
        return cls(
            team_signatures=ZVec(
                sorted(TeamSignature.of(state, team) for team in state.teams)
            )
        )
