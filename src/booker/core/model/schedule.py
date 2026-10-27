from __future__ import annotations

import dataclasses as dc

from javhar_util.immutables import ZSet

from booker.core.model.pairing import Pairing
from booker.core.model.state import State


@dc.dataclass(frozen=True, slots=True)
class Schedule:
    """
    A `State`, containing the live teams and the matches played between them previously,
    together with a set of `Pairing`s, which are matches to be played next.
    """

    state: State
    pairings: ZSet[Pairing]

    def __post_init__(self) -> None:
        for pairing in self.pairings:
            self.state.require_known(pairing.high)

    @classmethod
    def empty(cls, state: State) -> Schedule:
        return cls(state=state, pairings=ZSet([]))
