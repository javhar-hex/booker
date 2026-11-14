"""A progress file, saved so that an interrupted audit can resume."""

from __future__ import annotations

import dataclasses as dc
import json
import os
from pathlib import Path
from typing import Any

from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_progress import AuditProgress
from booker.verify.audit.audit_scope import AuditScope
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId

CHECKPOINT_INTERVAL = 1000

SCOPE_KEY = "scope"
NEXT_ID_KEY = "next_id"
STATES_KEY = "states"
# The file keeps the names of earlier audits: its "actions" are orbits.
ORBITS_KEY = "actions"
PAIRINGS_KEY = "pairings"


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

    def load(self) -> AuditProgress | None:
        "The progress an earlier audit of the same scope saved, if any."
        if not self.path.exists():
            return None
        return self._progress_in(json.loads(self.path.read_text()))

    def save(self, progress: AuditProgress) -> Checkpoint:
        "Atomically: a crash leaves the previous checkpoint, never half of the next."
        temporary = self.path.with_name(self.path.name + ".tmp")
        with open(temporary, "w") as file:
            json.dump(self._saved_dict(progress), file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, self.path)
        return self

    @property
    def _scope_dict(self) -> dict[str, str | int | None]:
        return {
            "db": str(self.scope.db_path),
            "mode": None
            if self.scope.reference_symmetry is None
            else self.scope.reference_symmetry.name,
            "from_id": _id_value(self.scope.state_id_range.start),
            "to_id": _id_value(self.scope.state_id_range.stop),
        }

    def _saved_dict(self, progress: AuditProgress) -> dict[str, Any]:
        return {
            SCOPE_KEY: self._scope_dict,
            NEXT_ID_KEY: _id_value(progress.next_state_id),
            STATES_KEY: progress.num_checked_states,
            ORBITS_KEY: progress.cml_pairing_count.orbits,
            PAIRINGS_KEY: progress.cml_pairing_count.pairings,
        }

    def _progress_in(self, saved: dict[str, Any]) -> AuditProgress:
        if saved[SCOPE_KEY] != self._scope_dict:
            raise AuditFailure(
                f"checkpoint is for another run: {saved[SCOPE_KEY]}, "
                f"not {self._scope_dict}"
            )
        return AuditProgress(
            next_state_id=None
            if saved[NEXT_ID_KEY] is None
            else StateId(value=saved[NEXT_ID_KEY]),
            num_checked_states=saved[STATES_KEY],
            cml_pairing_count=PairingCount(
                orbits=saved[ORBITS_KEY], pairings=saved[PAIRINGS_KEY]
            ),
        )


def _id_value(state_id: StateId | None) -> int | None:
    return None if state_id is None else state_id.value
