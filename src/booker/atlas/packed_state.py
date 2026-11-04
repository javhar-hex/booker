"""
The byte encoding of a `State`, used as the key of a position in the atlas.

Layout: `[n, code_0 .. code_{n-1}, adjacency]`. `n` is the number of live teams, each
`code_i` is `wins * ELIMINATION_LOSSES + losses` of team `i`, and `adjacency` is a
little-endian bitset with one bit per pair `i < j` in lexicographic order, set when the
two teams have met.
"""

from __future__ import annotations

import dataclasses as dc
import itertools
from collections.abc import Iterator

from javhar_util.immutables import ZSet, ZVec

from booker.core.model.invariants import (
    CHAMPION_WINS,
    ELIMINATION_LOSSES,
    NUM_PARTICIPANTS,
)
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team

BITS_PER_BYTE = 8


@dc.dataclass(frozen=True, slots=True)
class PackedState:
    "A `State` in bytes: the validated encoding, and nothing else."

    data: bytes

    def __post_init__(self) -> None:
        if not self.data or not 1 <= self.data[0] <= NUM_PARTICIPANTS:
            raise ValueError(f"need 1 to {NUM_PARTICIPANTS} teams in {self.data!r}")
        if len(self.data) != 1 + self.size + _adjacency_length(self.size):
            raise ValueError(f"wrong length for {self.size} teams: {len(self.data)}")
        if any(code > MAX_CODE for code in self._codes):
            raise ValueError(f"a record code exceeds {MAX_CODE}: {self.data!r}")
        if self._adjacency >> _pair_count(self.size):
            raise ValueError(f"adjacency bits beyond the last pair: {self.data!r}")

    @classmethod
    def of(cls, state: State) -> PackedState:
        met = {(p.low.index, p.high.index) for p in state.met}
        adjacency = sum(
            1 << bit for bit, pair in enumerate(_pairs(state.size)) if pair in met
        )
        return cls(
            data=bytes([state.size])
            + bytes(_code(record) for record in state.records)
            + adjacency.to_bytes(_adjacency_length(state.size), "little")
        )

    @property
    def size(self) -> int:
        return self.data[0]

    @property
    def state(self) -> State:
        met = (
            Pairing.of(Team(index=low), Team(index=high))
            for bit, (low, high) in enumerate(_pairs(self.size))
            if (self._adjacency >> bit) & 1
        )
        return State(records=ZVec(_record(code) for code in self._codes), met=ZSet(met))

    @property
    def _codes(self) -> bytes:
        return self.data[1 : 1 + self.size]

    @property
    def _adjacency(self) -> int:
        return int.from_bytes(self.data[1 + self.size :], "little")


def _code(record: Record) -> int:
    return record.wins * ELIMINATION_LOSSES + record.losses


def _record(code: int) -> Record:
    return Record(wins=code // ELIMINATION_LOSSES, losses=code % ELIMINATION_LOSSES)


def _adjacency_length(size: int) -> int:
    return -(-_pair_count(size) // BITS_PER_BYTE)


def _pairs(size: int) -> Iterator[tuple[int, int]]:
    "The adjacency bits' pairs, in bit order."
    return itertools.combinations(range(size), 2)


def _pair_count(size: int) -> int:
    return size * (size - 1) // 2


MAX_CODE = _code(Record(wins=CHAMPION_WINS, losses=ELIMINATION_LOSSES - 1))
