from pathlib import Path

import pytest

from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange

DB = Path("a.db")


def test_a_plan_without_a_range_is_the_whole_database() -> None:
    assert AuditPlan(db_path=DB, strict=None).is_whole_database


@pytest.mark.parametrize(
    "state_id_range",
    [
        StateIdRange(start=StateId(4)),
        StateIdRange(stop=StateId(4)),
        StateIdRange(start=StateId(2), stop=StateId(4)),
    ],
)
def test_a_plan_with_either_end_of_a_range_is_not(state_id_range: StateIdRange) -> None:
    assert not AuditPlan(
        db_path=DB, strict=None, state_id_range=state_id_range
    ).is_whole_database
