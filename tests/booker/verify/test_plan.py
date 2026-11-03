from booker.verify.isomorphism import IGRAPH, NETWORKX
from booker.verify.plan import AuditPlan, AuditReport, IdRange


def test_ranges_say_where_they_start_and_stop() -> None:
    assert str(IdRange()) == "[start, end)"
    assert str(IdRange(start=3, stop=9)) == "[3, 9)"


def test_only_a_range_from_the_start_is_the_whole_database() -> None:
    assert AuditPlan(db="a.db", mode=NETWORKX).is_whole_database
    assert AuditPlan(db="a.db", mode=NETWORKX, ids=IdRange(stop=4)).is_whole_database
    assert not AuditPlan(
        db="a.db", mode=NETWORKX, ids=IdRange(start=4)
    ).is_whole_database


def test_a_report_says_what_was_checked() -> None:
    report = AuditReport(
        ids=IdRange(start=2),
        mode=IGRAPH,
        states=1500,
        actions=3,
        pairings=4,
        is_solved=True,
        unexpanded=0,
    )

    assert str(report) == (
        "PASS: ids [2, end): checked 1,500 states / 3 actions (4 labelled pairings) "
        "with independent IGRAPH isomorphism, solved=True, unexpanded=0"
    )
