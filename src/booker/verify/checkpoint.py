"""A progress file, saved so that an interrupted audit can resume."""

from __future__ import annotations

import dataclasses as dc
import json
import os
from pathlib import Path
from typing import Any

from booker.verify.audit_failure import AuditFailure
from booker.verify.audit_plan import AuditPlan
from booker.verify.progress import Progress

CHECKPOINT_EVERY = 1000


@dc.dataclass(frozen=True, slots=True)
class Checkpoint:
    "A progress file for the audit of one scope."

    @dc.dataclass(frozen=True, slots=True)
    class Scope:
        "What an audit covers; progress saved for one scope means nothing for another."

        db: str
        mode: str | None
        from_id: int | None
        to_id: int | None

        @classmethod
        def of(cls, plan: AuditPlan) -> Checkpoint.Scope:
            return cls(
                db=os.path.abspath(plan.db),
                mode=None if plan.strict is None else plan.strict.name,
                from_id=plan.ids.start,
                to_id=plan.ids.stop,
            )

    path: str
    scope: Scope

    @classmethod
    def of(cls, plan: AuditPlan) -> Checkpoint | None:
        "The checkpoint that `plan` asks for, if it asks for one."
        if plan.checkpoint is None:
            return None
        return cls(path=plan.checkpoint, scope=cls.Scope.of(plan))

    def load(self) -> Progress | None:
        "The progress an earlier audit of the same scope saved, if any."
        if not Path(self.path).exists():
            return None
        saved: dict[str, Any] = json.loads(Path(self.path).read_text())
        if saved["scope"] != dc.asdict(self.scope):
            raise AuditFailure(
                f"checkpoint is for another run: {saved['scope']}, not {self.scope}"
            )
        return Progress(
            next_id=saved["next_id"],
            states=saved["states"],
            actions=saved["actions"],
            pairings=saved["pairings"],
        )

    def save(self, progress: Progress) -> None:
        "Atomically: a crash leaves the previous checkpoint, never half of the next."
        temporary = self.path + ".tmp"
        with open(temporary, "w") as f:
            json.dump({"scope": dc.asdict(self.scope), **dc.asdict(progress)}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, self.path)
