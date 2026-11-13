"""A progress file, saved so that an interrupted audit can resume."""

from __future__ import annotations

import dataclasses as dc
import json
import os
from pathlib import Path
from typing import Any

from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_scope import AuditScope
from booker.verify.audit.progress import Progress
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId

CHECKPOINT_EVERY = 1000


@dc.dataclass(frozen=True, slots=True)
class Checkpoint:
    "A progress file for the audit of one scope."

    path: Path
    scope: AuditScope

    @classmethod
    def of(cls, plan: AuditPlan) -> Checkpoint | None:
        "The checkpoint that `plan` asks for, if it asks for one."
        if plan.checkpoint is None:
            return None
        return cls(path=plan.checkpoint, scope=AuditScope.of(plan))

    def load(self) -> Progress | None:
        "The progress an earlier audit of the same scope saved, if any."
        if not self.path.exists():
            return None
        saved: dict[str, Any] = json.loads(self.path.read_text())
        if saved["scope"] != dc.asdict(self.scope):
            raise AuditFailure(
                f"checkpoint is for another run: {saved['scope']}, not {self.scope}"
            )
        return Progress(
            next_id=None
            if saved["next_id"] is None
            else StateId(value=saved["next_id"]),
            states=saved["states"],
            counted=PairingCount(orbits=saved["actions"], pairings=saved["pairings"]),
        )

    def save(self, progress: Progress) -> None:
        "Atomically: a crash leaves the previous checkpoint, never half of the next."
        temporary = self.path.with_name(self.path.name + ".tmp")
        with open(temporary, "w") as f:
            json.dump(
                {
                    "scope": dc.asdict(self.scope),
                    "next_id": None
                    if progress.next_id is None
                    else progress.next_id.value,
                    "states": progress.states,
                    # The file keeps the names of earlier audits: its actions are orbits.
                    "actions": progress.counted.orbits,
                    "pairings": progress.counted.pairings,
                },
                f,
            )
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, self.path)
