"""What an audit found."""

from __future__ import annotations

import dataclasses as dc

from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.id_range import IdRange
from booker.verify.audit.progress import Progress
from booker.verify.spot_check.pairing_count import PairingCount


@dc.dataclass(frozen=True, slots=True)
class AuditReport:
    ids: IdRange
    strict: StateSymmetry | None
    states: int
    counted: PairingCount
    is_solved: bool
    unexpanded: int

    @classmethod
    def of(
        cls, plan: AuditPlan, progress: Progress, is_solved: bool, unexpanded: int
    ) -> AuditReport:
        "What an audit of `plan` found, having got as far as `progress`."
        return cls(
            ids=plan.ids,
            strict=plan.strict,
            states=progress.states,
            counted=progress.counted,
            is_solved=is_solved,
            unexpanded=unexpanded,
        )

    def __str__(self) -> str:
        how = (
            "children and orbits not compared"
            if self.strict is None
            else f"children and orbits compared by {self.strict.name}"
        )
        return (
            f"PASS: ids {self.ids}: checked {self.states:,} states / "
            f"{self.counted.orbits:,} actions ({self.counted.pairings:,} labelled pairings), {how}, "
            f"solved={self.is_solved}, unexpanded={self.unexpanded:,}"
        )
