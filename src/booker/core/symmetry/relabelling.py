"""Permutations of the teams of a state, and their effect on what names teams."""

from __future__ import annotations

import dataclasses as dc
from collections.abc import Sequence

from javhar_util.immutables import ZMap, ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.model.team import Team


@dc.dataclass(frozen=True, slots=True)
class Relabelling:
    "A permutation of teams."

    images: ZMap[Team, Team]

    def __post_init__(self) -> None:
        teams = {Team(index=idx) for idx in range(len(self.images))}
        if set(self.images.keys()) != teams or set(self.images.values()) != teams:
            raise ValueError(f"not a permutation of {len(teams)} teams: {self.images}")

    @classmethod
    def of(cls, indices: Sequence[int]) -> Relabelling:
        "Team `idx_pre` becomes team `indices[idx_pre]`."
        return cls(
            images=ZMap(
                {
                    Team(index=idx_pre): Team(index=idx_post)
                    for idx_pre, idx_post in enumerate(indices)
                }
            )
        )

    def __len__(self) -> int:
        return len(self.images)

    def schedule(self, schedule: Schedule) -> Schedule:
        return Schedule(
            state=self.state(schedule.state), pairings=self.pairings(schedule.pairings)
        )

    def state(self, state: State) -> State:
        self._require_size(state)
        preimage = {image: team for team, image in self.images.items()}
        return State(
            records=ZVec(state.record(preimage[team]) for team in state.teams),
            past_pairings=self.pairings(state.past_pairings),
        )

    def pairings(self, pairings: ZSet[Pairing]) -> ZSet[Pairing]:
        return ZSet(self.pairing(pairing) for pairing in pairings)

    def pairing(self, pairing: Pairing) -> Pairing:
        return Pairing.of(self.team(pairing.lhs), self.team(pairing.rhs))

    def team(self, team: Team) -> Team:
        return self.images[team]

    def _require_size(self, state: State) -> None:
        if state.size != len(self):
            raise ValueError(f"relabels {len(self)} teams, not {state.size}")
