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
        if saved["scope"] != self._scope_as_json:
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
        with open(temporary, "w") as file:
            json.dump(
                {
                    "scope": self._scope_as_json,
                    "next_id": _id_value(progress.next_id),
                    "states": progress.states,
                    # The file keeps the names of earlier audits: its actions are orbits.
                    "actions": progress.counted.orbits,
                    "pairings": progress.counted.pairings,
                },
                file,
            )
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, self.path)

    @property
    def _scope_as_json(self) -> dict[str, str | int | None]:
        return {
            "db": str(self.scope.db_path),
            "mode": None if self.scope.strict is None else self.scope.strict.name,
            "from_id": _id_value(self.scope.state_id_range.start),
            "to_id": _id_value(self.scope.state_id_range.stop),
        }


def _id_value(state_id: StateId | None) -> int | None:
    return None if state_id is None else state_id.value
