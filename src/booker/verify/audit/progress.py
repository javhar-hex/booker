"""How far an audit has got."""

from __future__ import annotations

import dataclasses as dc

from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


@dc.dataclass(frozen=True, slots=True)
class Progress:
    "How far an audit has got, and what it has counted on the way."

    next_id: StateId | None
    states: int
    counted: PairingCount

    @classmethod
    def start(cls, ids: StateIdRange) -> Progress:
        "Nothing is checked yet: the next id is the first of `ids`, if it has one."
        return cls(next_id=ids.start, states=0, counted=PairingCount.none())

    def after(self, state: StateId, counted: PairingCount) -> Progress:
        return Progress(
            next_id=StateId(value=state.value + 1),
            states=self.states + 1,
            counted=self.counted.plus(counted),
        )
