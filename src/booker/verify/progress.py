"""How far an audit has got."""

from __future__ import annotations

import dataclasses as dc

from booker.verify.id_range import IdRange
from booker.verify.state_id import StateId

BEFORE_ANY_ID = -1


@dc.dataclass(frozen=True, slots=True)
class Progress:
    "How far an audit has got, and what it has counted on the way."

    next_id: int
    states: int
    actions: int
    pairings: int

    @classmethod
    def start(cls, ids: IdRange) -> Progress:
        first = BEFORE_ANY_ID if ids.start is None else ids.start
        return cls(next_id=first, states=0, actions=0, pairings=0)

    def after(self, state: StateId, actions: int, pairings: int) -> Progress:
        return Progress(
            next_id=state.value + 1,
            states=self.states + 1,
            actions=self.actions + actions,
            pairings=self.pairings + pairings,
        )
