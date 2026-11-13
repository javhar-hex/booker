"""The audit: every position of the atlas, in order, against the rules."""

from __future__ import annotations

from collections.abc import Callable

from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_progress import AuditProgress
from booker.verify.audit.audit_report import AuditReport
from booker.verify.audit.checkpoint import CHECKPOINT_INTERVAL, Checkpoint
from booker.verify.audit.global_check import GlobalCheck
from booker.verify.spot_check.atlas_reader import AtlasReader
from booker.verify.spot_check.state_check import StateCheck
from booker.verify.spot_check.state_id_range import StateIdRange

REPORT_INTERVAL = 10000


def audit(plan: AuditPlan, log: Callable[[str], None]) -> AuditReport:
    "Raises `AuditFailure` at the first thing wrong; `log` hears of progress."
    with AtlasReader.open(plan.db_path) as atlas_reader:
        global_check = GlobalCheck(atlas_reader)
        global_check.check_metadata()
        num_unexpanded_states = atlas_reader.num_unexpanded()
        is_solved = atlas_reader.num_unsolved() == 0
        if plan.is_whole_database:
            global_check.check_whole_database(plan)
        progress = _walk(atlas_reader, plan, is_solved, log)
        if plan.is_whole_database and plan.expected_root_gtv is not None:
            global_check.check_root_gtv(plan.expected_root_gtv)
    return AuditReport.of(plan, progress, is_solved, num_unexpanded_states)


def _walk(
    atlas_reader: AtlasReader,
    plan: AuditPlan,
    is_solved: bool,
    log: Callable[[str], None],
) -> AuditProgress:
    checkpoint = Checkpoint.of(plan)
    progress = (checkpoint and checkpoint.load()) or AuditProgress.start(
        plan.state_id_range
    )
    if progress.num_checked_states:
        log(
            f"resuming at id {progress.next_state_id} after {progress.num_checked_states:,} states"
        )
    check = StateCheck(
        db=atlas_reader, symmetry=plan.reference_symmetry, is_solved=is_solved
    )
    remaining = StateIdRange(start=progress.next_state_id, stop=plan.state_id_range.stop)
    for state_id in atlas_reader.state_ids(remaining):
        progress = progress.after(state_id, check.run(state_id))
        if checkpoint and _is_time_to_save(progress, plan):
            checkpoint.save(progress)
        if (
            plan.max_num_states is not None
            and progress.num_checked_states >= plan.max_num_states
        ):
            break
        if progress.num_checked_states % REPORT_INTERVAL == 0:
            log(
                f"checked {progress.num_checked_states:,} states, {progress.cml_pairing_count.orbits:,} actions"
            )
    return progress


def _is_time_to_save(progress: AuditProgress, plan: AuditPlan) -> bool:
    return (
        progress.num_checked_states % CHECKPOINT_INTERVAL == 0
        or progress.num_checked_states == plan.max_num_states
    )
