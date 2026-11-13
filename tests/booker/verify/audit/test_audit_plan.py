from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.spot_check.state_id_range import StateIdRange


def test_only_a_range_from_the_start_is_the_whole_database() -> None:
    assert AuditPlan(db="a.db", strict=None).is_whole_database
    assert AuditPlan(
        db="a.db", strict=None, ids=StateIdRange.of(stop=4)
    ).is_whole_database
    assert not AuditPlan(
        db="a.db", strict=None, ids=StateIdRange.of(start=4)
    ).is_whole_database
