"""What an audit found."""

from __future__ import annotations

import dataclasses as dc

from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_progress import AuditProgress
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id_range import StateIdRange


@dc.dataclass(frozen=True, slots=True)
class AuditReport:
    state_id_range: StateIdRange
    reference_symmetry: StateSymmetry | None
    num_checked_states: int
    cml_pairing_count: PairingCount
    is_solved: bool
    unexpanded: int

    @classmethod
    def of(
        cls, plan: AuditPlan, progress: AuditProgress, is_solved: bool, unexpanded: int
    ) -> AuditReport:
        "What an audit of `plan` found, having got as far as `progress`."
        return cls(
            state_id_range=plan.state_id_range,
            reference_symmetry=plan.reference_symmetry,
            num_checked_states=progress.num_checked_states,
            cml_pairing_count=progress.cml_pairing_count,
            is_solved=is_solved,
            unexpanded=unexpanded,
        )

    def __str__(self) -> str:
        how = (
            "children and orbits not compared"
            if self.reference_symmetry is None
            else f"children and orbits compared by {self.reference_symmetry.name}"
        )
        return (
            f"PASS: ids {self.state_id_range}: checked {self.num_checked_states:,} states / "
            f"{self.cml_pairing_count.orbits:,} actions ({self.cml_pairing_count.pairings:,} labelled pairings), {how}, "
            f"solved={self.is_solved}, unexpanded={self.unexpanded:,}"
        )
