"""A position as the verifier reads it from an atlas key, with no rules attached."""

from __future__ import annotations

import dataclasses as dc
import itertools

from javhar_util.immutables import ZSet, ZVec

from booker.verify.failure import AuditFailure
from booker.verify.spec import CHAMPION_WINS, ELIMINATION_LOSSES, NUM_TEAMS

MAX_CODE = CHAMPION_WINS * ELIMINATION_LOSSES + ELIMINATION_LOSSES - 1
BITS_PER_BYTE = 8


@dc.dataclass(frozen=True, slots=True, order=True)
class Standing:
    "A team's wins and losses."

    wins: int
    losses: int

    def __post_init__(self) -> None:
        if not 0 <= self.wins <= CHAMPION_WINS:
            raise ValueError(f"wins must be in [0, {CHAMPION_WINS}], got {self.wins}")
        if not 0 <= self.losses <= ELIMINATION_LOSSES:
            raise ValueError(
                f"losses must be in [0, {ELIMINATION_LOSSES}]: {self.losses}"
            )

    @property
    def colour(self) -> int:
        "Distinct for every standing, as the key's record code is."
        return self.wins * ELIMINATION_LOSSES + self.losses

    @property
    def is_unbeaten(self) -> bool:
        return self.losses == 0


@dc.dataclass(frozen=True, slots=True, order=True)
class Pair:
    "Two distinct teams, by index in a position, the lower first."

    low: int
    high: int

    def __post_init__(self) -> None:
        if not 0 <= self.low < self.high:
            raise ValueError(f"need 0 <= low < high, got {self.low} and {self.high}")

    def involves(self, team: int) -> bool:
        return team in (self.low, self.high)


@dc.dataclass(frozen=True, slots=True)
class Position:
    "The live teams' standings, and which of them have met. Nothing more is checked."

    standings: ZVec[Standing]
    meetings: ZSet[Pair]

    def __post_init__(self) -> None:
        if not 1 <= len(self.standings) <= NUM_TEAMS:
            raise ValueError(f"need 1 to {NUM_TEAMS} teams, got {len(self.standings)}")
        if any(meeting.high >= len(self.standings) for meeting in self.meetings):
            raise ValueError(f"a meeting is between teams beyond {self.size}")

    @classmethod
    def opening(cls) -> Position:
        return cls(
            standings=ZVec([Standing(wins=0, losses=0)] * NUM_TEAMS), meetings=ZSet([])
        )

    @classmethod
    def parse(cls, key: bytes) -> Position:
        "The key is `[n, n record codes, adjacency bitset]`; anything else is a failure."
        size = key[0] if key else 0
        if not 1 <= size <= NUM_TEAMS:
            raise AuditFailure(f"key claims {size} teams: {key!r}")
        pairs = list(itertools.combinations(range(size), 2))
        if len(key) != 1 + size + -(-len(pairs) // BITS_PER_BYTE):
            raise AuditFailure(
                f"key of {len(key)} bytes cannot hold {size} teams: {key!r}"
            )
        if any(code > MAX_CODE for code in key[1 : 1 + size]):
            raise AuditFailure(f"key has a record beyond a champion's: {key!r}")
        adjacency = int.from_bytes(key[1 + size :], "little")
        if adjacency >> len(pairs):
            raise AuditFailure(f"key has adjacency bits beyond its last pair: {key!r}")
        return cls(
            standings=ZVec(
                Standing(
                    wins=code // ELIMINATION_LOSSES, losses=code % ELIMINATION_LOSSES
                )
                for code in key[1 : 1 + size]
            ),
            meetings=ZSet(
                Pair(low=low, high=high)
                for bit, (low, high) in enumerate(pairs)
                if (adjacency >> bit) & 1
            ),
        )

    @property
    def size(self) -> int:
        return len(self.standings)

    @property
    def is_decided(self) -> bool:
        return self.size == 1

    @property
    def num_unbeaten(self) -> int:
        return sum(standing.is_unbeaten for standing in self.standings)

    @property
    def depth(self) -> int:
        "The matches played so far: each one has cost a team one loss."
        eliminated = NUM_TEAMS - self.size
        return eliminated * ELIMINATION_LOSSES + sum(s.losses for s in self.standings)
