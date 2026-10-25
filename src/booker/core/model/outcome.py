from __future__ import annotations

import dataclasses as dc
import itertools
from collections.abc import Iterator

from booker.core.model.pairing import Pairing
from booker.core.model.team import Team
from util.dtypes.immutables.z_map import ZMap
from util.dtypes.immutables.z_set import ZSet


@dc.dataclass(frozen=True, slots=True)
class Outcome:
    "The Collider's move: the winner of each scheduled pairing."

    winners: ZMap[Pairing, Team]

    def __post_init__(self) -> None:
        for pairing, winner in self.winners.items():
            if not pairing.involves(winner):
                raise ValueError(f"{winner} cannot win {pairing}, not being in it")

    @classmethod
    def every(cls, pairings: ZSet[Pairing]) -> Iterator[Outcome]:
        "All 2^k outcomes of k pairings."
        ordered = sorted(pairings)
        for winners in itertools.product(*((p.low, p.high) for p in ordered)):
            yield cls(winners=ZMap(zip(ordered, winners)))

    @property
    def pairings(self) -> ZSet[Pairing]:
        return ZSet(self.winners.keys())

    def winner(self, pairing: Pairing) -> Team:
        return self.winners[pairing]

    def loser(self, pairing: Pairing) -> Team:
        return pairing.opponent(self.winner(pairing))
