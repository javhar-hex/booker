"""What an audit covers."""

from __future__ import annotations

import dataclasses as dc
from pathlib import Path

from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.spot_check.state_id_range import StateIdRange


@dc.dataclass(frozen=True, slots=True)
class AuditScope:
    "What an audit covers; progress saved for one scope means nothing for another."

    db: Path
    mode: str | None
    ids: StateIdRange

    @classmethod
    def of(cls, plan: AuditPlan) -> AuditScope:
        return cls(
            db=plan.db.resolve(),
            mode=None if plan.strict is None else plan.strict.name,
            ids=plan.ids,
        )
