"""The audit: every position of the atlas, in order, against the rules."""

from __future__ import annotations

import dataclasses as dc
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


@dc.dataclass(frozen=True, slots=True)
class AtlasAuditor:
    "Carries out `plan`: the checks of the whole atlas, and of every position in its range."

    plan: AuditPlan
    log: Callable[[str], None]

    def audit(self) -> AuditReport:
        "Raises `AuditFailure` at the first thing wrong; `log` hears of progress."
        with AtlasReader.open(self.plan.db_path) as atlas_reader:
            global_check = GlobalCheck(atlas_reader)
            global_check.check_metadata()
            num_unexpanded_states = atlas_reader.num_unexpanded()
            is_solved = atlas_reader.num_unsolved() == 0
            if self.plan.is_whole_database:
                global_check.check_whole_database(self.plan)
            audit_progress = self._walk(atlas_reader, is_solved)
            if self.plan.is_whole_database and self.plan.expected_root_gtv is not None:
                global_check.check_root_gtv(self.plan.expected_root_gtv)
        return AuditReport.of(
            self.plan, audit_progress, is_solved, num_unexpanded_states
        )

    def _walk(self, atlas_reader: AtlasReader, is_solved: bool) -> AuditProgress:
        checkpoint = Checkpoint.of(self.plan)
        progress = self._starting_progress(checkpoint)
        state_check = StateCheck(
            atlas_reader=atlas_reader,
            symmetry=self.plan.reference_symmetry,
            is_solved=is_solved,
        )
        remaining = StateIdRange(
            start=progress.next_state_id, stop=self.plan.state_id_range.stop
        )
        for state_id in atlas_reader.state_ids(remaining):
            progress = progress.after(state_id, state_check.run(state_id))
            self._possibly_save(checkpoint, progress)
            if self._is_max_num_states_reached(progress):
                break
            self._possibly_log(progress)
        return progress

    def _starting_progress(self, checkpoint: Checkpoint | None) -> AuditProgress:
        saved = None if checkpoint is None else checkpoint.load()
        if saved is None:
            return AuditProgress.start(self.plan.state_id_range)
        self.log(
            f"resuming at id {saved.next_state_id} "
            f"after {saved.num_checked_states:,} states"
        )
        return saved

    def _possibly_save(
        self, checkpoint: Checkpoint | None, progress: AuditProgress
    ) -> None:
        "Saves at every `CHECKPOINT_INTERVAL` states, and when the last state is checked."
        is_time_to_save = (
            progress.num_checked_states % CHECKPOINT_INTERVAL == 0
            or progress.num_checked_states == self.plan.max_num_states
        )
        if checkpoint is not None and is_time_to_save:
            checkpoint.save(progress)

    def _is_max_num_states_reached(self, progress: AuditProgress) -> bool:
        return (
            self.plan.max_num_states is not None
            and progress.num_checked_states >= self.plan.max_num_states
        )

    def _possibly_log(self, progress: AuditProgress) -> None:
        "Logs at every `REPORT_INTERVAL` states."
        if progress.num_checked_states % REPORT_INTERVAL == 0:
            self.log(
                f"checked {progress.num_checked_states:,} states, "
                f"{progress.cml_pairing_count.orbits:,} actions"
            )
