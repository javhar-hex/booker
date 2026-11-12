from booker.core.symmetry.state_symmetries import VF2
from booker.verify.audit_report import AuditReport
from booker.verify.id_range import IdRange


def test_a_report_says_what_was_checked() -> None:
    report = AuditReport(
        ids=IdRange(start=2),
        strict=VF2,
        states=1500,
        actions=3,
        pairings=4,
        is_solved=True,
        unexpanded=0,
    )

    assert str(report) == (
        "PASS: ids [2, end): checked 1,500 states / 3 actions (4 labelled pairings), "
        "children and orbits compared by vf2, solved=True, unexpanded=0"
    )


def test_a_report_says_when_children_and_orbits_were_not_compared() -> None:
    report = AuditReport(
        ids=IdRange(),
        strict=None,
        states=1,
        actions=2,
        pairings=3,
        is_solved=False,
        unexpanded=5,
    )

    assert str(report) == (
        "PASS: ids [start, end): checked 1 states / 2 actions (3 labelled pairings), "
        "children and orbits not compared, solved=False, unexpanded=5"
    )
