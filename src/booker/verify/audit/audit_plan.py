"""What to audit."""

from __future__ import annotations

import dataclasses as dc
from pathlib import Path

from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.verify.spot_check.state_id_range import StateIdRange


@dc.dataclass(frozen=True, slots=True)
class AuditPlan:
    """
    The checks on the states in `ids` and their actions. Whole-database checks run only
    in the range that starts at the beginning, so a set of ranges partitioning the ids
    checks everything exactly once. With `limit`, at most that many states in all are
    checked, counting those of earlier sittings resumed from `checkpoint`.

    Whether the stored children and pairings are the right ones is checked cheaply, by
    what a state's records and meetings must add up to. With `strict`, every child is also
    compared with the successor it should be, and every orbit found again, by that
    implementation of the symmetries of states: slow, and a check of the generator.
    """

    db: Path
    ids: StateIdRange = dc.field(default_factory=StateIdRange)
    strict: StateSymmetry | None = None
    limit: int | None = None
    expect_root: int | None = None
    require_complete: bool = False
    checkpoint: Path | None = None

    @property
    def is_whole_database(self) -> bool:
        return self.ids.start is None
