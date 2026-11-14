"""What to audit."""

from __future__ import annotations

import dataclasses as dc
from pathlib import Path

from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.verify.spot_check.state_id_range import StateIdRange


@dc.dataclass(frozen=True, slots=True)
class AuditPlan:
    """
    The checks on the states in `state_id_range` and their actions. Whole-database checks
    run only when there is no range, so a set of ranges partitioning the ids needs one run
    more for them. With `max_num_states` (at least 1), at most that many states in all are
    checked, counting those of earlier sittings resumed from `checkpoint`. The `db_path` is
    absolute, so that progress saved for it cannot be taken for progress on another file.

    Whether the stored children and pairings are the right ones is checked cheaply, by
    what a state's records and meetings must add up to. With `reference_symmetry`, every
    child is also compared with the successor it should be, and every orbit found again,
    by that implementation of the symmetries of states: slow, and a check of the
    generator. With `expected_root_gtv`, the whole-database checks include that the root
    has the expected GTV.
    """

    db_path: Path
    state_id_range: StateIdRange = dc.field(default_factory=StateIdRange)
    reference_symmetry: StateSymmetry | None = None
    max_num_states: int | None = None
    expected_root_gtv: int | None = None
    require_complete: bool = False
    checkpoint: Path | None = None

    def __post_init__(self) -> None:
        if not self.db_path.is_absolute():
            raise ValueError(
                f"db_path must be absolute, so it names one file: {self.db_path}"
            )
        if self.max_num_states is not None and self.max_num_states < 1:
            raise ValueError(f"max_num_states must be at least 1: {self.max_num_states}")

    @property
    def is_whole_database(self) -> bool:
        return self.state_id_range.start is None and self.state_id_range.stop is None
