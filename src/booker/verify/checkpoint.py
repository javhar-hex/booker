"""Progress through an audit, saved so that an interrupted audit can resume."""

from __future__ import annotations

import dataclasses as dc
import json
import os
from pathlib import Path
from typing import Any

from booker.verify.database import StateId
from booker.verify.failure import AuditFailure
from booker.verify.plan import AuditPlan, IdRange

CHECKPOINT_EVERY = 1000
BEFORE_ANY_ID = -1


@dc.dataclass(frozen=True, slots=True)
class Progress:
    "How far an audit has got, and what it has counted on the way."

    next_id: int
    states: int
    actions: int
    pairings: int

    @classmethod
    def start(cls, ids: IdRange) -> Progress:
        first = BEFORE_ANY_ID if ids.start is None else ids.start
        return cls(next_id=first, states=0, actions=0, pairings=0)

    def after(self, state: StateId, actions: int, pairings: int) -> Progress:
        return Progress(
            next_id=state.value + 1,
            states=self.states + 1,
            actions=self.actions + actions,
            pairings=self.pairings + pairings,
        )


@dc.dataclass(frozen=True, slots=True)
class Scope:
    "What an audit covers; progress saved for one scope means nothing for another."

    db: str
    mode: str | None
    from_id: int | None
    to_id: int | None

    @classmethod
    def of(cls, plan: AuditPlan) -> Scope:
        return cls(
            db=os.path.abspath(plan.db),
            mode=None if plan.strict is None else plan.strict.name,
            from_id=plan.ids.start,
            to_id=plan.ids.stop,
        )


@dc.dataclass(frozen=True, slots=True)
class Checkpoint:
    "A progress file for the audit of one scope."

    path: str
    scope: Scope

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
