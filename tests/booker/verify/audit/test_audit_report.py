from pathlib import Path

from booker.core.symmetry.state_symmetries import VF2
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_progress import AuditProgress
from booker.verify.audit.audit_report import AuditReport
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


def test_a_report_says_what_was_checked() -> None:
    report = AuditReport(
        state_id_range=StateIdRange(start=StateId(2)),
        reference_symmetry=VF2,
        num_checked_states=1500,
        cml_pairing_count=PairingCount(orbits=3, pairings=4),
        is_solved=True,
        num_unexpanded_states=0,
    )

    assert str(report) == (
        "PASS: ids [2, end): checked 1,500 states / 3 actions (4 labelled pairings), "
        "children and orbits compared by vf2, solved=True, unexpanded=0"
    )


def test_a_report_says_when_children_and_orbits_were_not_compared() -> None:
    report = AuditReport(
        state_id_range=StateIdRange(),
        reference_symmetry=None,
        num_checked_states=1,
        cml_pairing_count=PairingCount(orbits=2, pairings=3),
        is_solved=False,
        num_unexpanded_states=5,
    )

    assert str(report) == (
        "PASS: ids [start, end): checked 1 states / 2 actions (3 labelled pairings), "
        "children and orbits not compared, solved=False, unexpanded=5"
    )


def test_a_report_is_made_of_the_plan_and_the_progress_and_what_was_counted() -> None:
    plan = AuditPlan(
        db_path=Path("/data/atlas.db"),
        reference_symmetry=VF2,
        state_id_range=StateIdRange(start=StateId(2)),
    )
    progress = AuditProgress(
        next_state_id=StateId(value=9),
        num_checked_states=7,
        cml_pairing_count=PairingCount(orbits=30, pairings=44),
    )

    report = AuditReport.of(plan, progress, is_solved=True, num_unexpanded_states=5)

    assert report == AuditReport(
        state_id_range=StateIdRange(start=StateId(2)),
        reference_symmetry=VF2,
        num_checked_states=7,
        cml_pairing_count=PairingCount(orbits=30, pairings=44),
        is_solved=True,
        num_unexpanded_states=5,
    )
