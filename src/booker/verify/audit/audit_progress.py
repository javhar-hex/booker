"""How far an audit has got."""

from __future__ import annotations

import dataclasses as dc

from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


@dc.dataclass(frozen=True, slots=True)
class AuditProgress:
    "How far an audit has got, and the pairings it has counted on the way."

    next_state_id: StateId | None
    num_checked_states: int
    cml_pairing_count: PairingCount

    @classmethod
    def start(cls, state_id_range: StateIdRange) -> AuditProgress:
        "Nothing is checked yet: the next id is the first of `state_id_range`, if it has one."
        return cls(
            next_state_id=state_id_range.start,
            num_checked_states=0,
            cml_pairing_count=PairingCount.none(),
        )

    def after(self, state_id: StateId, pairing_count: PairingCount) -> AuditProgress:
        return AuditProgress(
            next_state_id=StateId(value=state_id.value + 1),
            num_checked_states=self.num_checked_states + 1,
            cml_pairing_count=self.cml_pairing_count.plus(pairing_count),
        )
