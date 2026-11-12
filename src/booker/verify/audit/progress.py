"""How far an audit has got."""

from __future__ import annotations

import dataclasses as dc

from booker.verify.audit.id_range import IdRange
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId

BEFORE_ANY_ID = -1


@dc.dataclass(frozen=True, slots=True)
class Progress:
    "How far an audit has got, and what it has counted on the way."

    next_id: int
    states: int
    counted: PairingCount

    @classmethod
    def start(cls, ids: IdRange) -> Progress:
        first = BEFORE_ANY_ID if ids.start is None else ids.start
        return cls(next_id=first, states=0, counted=PairingCount.none())

    def after(self, state: StateId, counted: PairingCount) -> Progress:
        return Progress(
            next_id=state.value + 1,
            states=self.states + 1,
            counted=self.counted.plus(counted),
        )
