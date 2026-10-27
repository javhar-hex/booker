from __future__ import annotations

import dataclasses as dc

from javhar_util.immutables import ZSet, ZVec

from booker.core.model.invariants import ELIMINATION_LOSSES, NUM_PARTICIPANTS
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.team import Team


@dc.dataclass(frozen=True, slots=True)
class State:
    """
    A collection of live teams, with information about which teams have already met
    before. This encodes a graph where the nodes are the teams and the edges are
    previously played matches.
    Each team is represented by a pointer to its `Record`.
    """

    records: ZVec[Record]
    met: ZSet[Pairing]

    def __post_init__(self) -> None:
        if not 1 <= len(self.records) <= NUM_PARTICIPANTS:
            raise ValueError(
                f"need 1 to {NUM_PARTICIPANTS} live teams, got {len(self.records)}"
            )
        if any(record.is_eliminated for record in self.records):
            raise ValueError("eliminated teams are not part of the state")
        for pairing in self.met:
            self._require_meetable(pairing)

    @classmethod
    def start(cls) -> State:
        return cls(records=ZVec([Record.fresh()] * NUM_PARTICIPANTS), met=ZSet([]))

    def __contains__(self, team: Team) -> bool:
        return team.index < self.size

    @property
    def size(self) -> int:
        return len(self.records)

    @property
    def teams(self) -> ZVec[Team]:
        return ZVec(Team(index=i) for i in range(self.size))

    @property
    def is_decided(self) -> bool:
        return self.size == 1

    @property
    def matches_played(self) -> int:
        "Since the start of the tournament: every match costs exactly one team a life."
        eliminated = NUM_PARTICIPANTS - self.size
        return eliminated * ELIMINATION_LOSSES + sum(
            record.losses for record in self.records
        )

    def record(self, team: Team) -> Record:
        self.require_known(team)
        return self.records[team.index]

    def require_known(self, team: Team) -> None:
        if team not in self:
            raise ValueError(f"{team} is not one of the {self.size} live teams")

    def has_met(self, pairing: Pairing) -> bool:
        return pairing in self.met

    def rematches(self, pairings: ZSet[Pairing]) -> int:
        return sum(self.has_met(pairing) for pairing in pairings)

    def _require_meetable(self, pairing: Pairing) -> None:
        if all(self.record(team).is_unbeaten for team in (pairing.low, pairing.high)):
            raise ValueError(f"two unbeaten teams cannot have met: {pairing}")
