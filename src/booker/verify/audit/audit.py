"""The audit: every position of the atlas, in order, against the rules."""

from __future__ import annotations

from collections.abc import Callable

from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_report import AuditReport
from booker.verify.audit.checkpoint import CHECKPOINT_EVERY, Checkpoint
from booker.verify.audit.progress import Progress
from booker.verify.audit.whole_database import (
    check_metadata,
    check_root_gtv,
    check_whole_database,
)
from booker.verify.spot_check.atlas_reader import AtlasReader
from booker.verify.spot_check.state_check import StateCheck
from booker.verify.spot_check.state_id_range import StateIdRange

REPORT_EVERY = 10000


def audit(plan: AuditPlan, log: Callable[[str], None]) -> AuditReport:
    "Raises `AuditFailure` at the first thing wrong; `log` hears of progress."
    with AtlasReader.open(plan.db_path) as db:
        root = check_metadata(db)
        unexpanded = db.num_unexpanded()
        is_solved = db.num_unsolved() == 0
        if plan.is_whole_database:
            check_whole_database(db, plan, root)
        progress = _walk(db, plan, is_solved, log)
        if plan.is_whole_database and plan.expected_root_gtv is not None:
            check_root_gtv(db, root, plan.expected_root_gtv)
    return AuditReport.of(plan, progress, is_solved, unexpanded)


def _walk(
    db: AtlasReader, plan: AuditPlan, is_solved: bool, log: Callable[[str], None]
) -> Progress:
    checkpoint = Checkpoint.of(plan)
    progress = (checkpoint and checkpoint.load()) or Progress.start(plan.state_id_range)
    if progress.states:
        log(f"resuming at id {progress.next_id} after {progress.states:,} states")
    check = StateCheck(db=db, symmetry=plan.reference_symmetry, is_solved=is_solved)
    remaining = StateIdRange(start=progress.next_id, stop=plan.state_id_range.stop)
    for state_id in db.state_ids(remaining):
        progress = progress.after(state_id, check.run(state_id))
        if checkpoint and _is_time_to_save(progress, plan):
            checkpoint.save(progress)
        if plan.max_num_states is not None and progress.states >= plan.max_num_states:
            break
        if progress.states % REPORT_EVERY == 0:
            log(
                f"checked {progress.states:,} states, {progress.counted.orbits:,} actions"
            )
    return progress


def _is_time_to_save(progress: Progress, plan: AuditPlan) -> bool:
    return (
        progress.states % CHECKPOINT_EVERY == 0 or progress.states == plan.max_num_states
    )
