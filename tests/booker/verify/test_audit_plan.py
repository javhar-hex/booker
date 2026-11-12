from booker.verify.audit_plan import AuditPlan
from booker.verify.id_range import IdRange


def test_only_a_range_from_the_start_is_the_whole_database() -> None:
    assert AuditPlan(db="a.db", strict=None).is_whole_database
    assert AuditPlan(db="a.db", strict=None, ids=IdRange(stop=4)).is_whole_database
    assert not AuditPlan(db="a.db", strict=None, ids=IdRange(start=4)).is_whole_database
