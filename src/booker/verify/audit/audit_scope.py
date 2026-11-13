"""What an audit covers."""

from __future__ import annotations

import dataclasses as dc
import os

from booker.verify.audit.audit_plan import AuditPlan


@dc.dataclass(frozen=True, slots=True)
class AuditScope:
    "What an audit covers; progress saved for one scope means nothing for another."

    db: str
    mode: str | None
    from_id: int | None
    to_id: int | None

    @classmethod
    def of(cls, plan: AuditPlan) -> AuditScope:
        return cls(
            db=os.path.abspath(plan.db),
            mode=None if plan.strict is None else plan.strict.name,
            from_id=None if plan.ids.start is None else plan.ids.start.value,
            to_id=None if plan.ids.stop is None else plan.ids.stop.value,
        )
