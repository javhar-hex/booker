"""What an audit covers."""

from __future__ import annotations

import dataclasses as dc
from pathlib import Path

from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.spot_check.state_id_range import StateIdRange


@dc.dataclass(frozen=True, slots=True)
class AuditScope:
    "What an audit covers; progress saved for one scope means nothing for another."

    db_path: Path
    reference_symmetry: StateSymmetry | None
    state_id_range: StateIdRange

    @classmethod
    def of(cls, plan: AuditPlan) -> AuditScope:
        return cls(
            db_path=plan.db_path,
            reference_symmetry=plan.reference_symmetry,
            state_id_range=plan.state_id_range,
        )
