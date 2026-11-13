from pathlib import Path

from booker.core.symmetry.state_symmetries import BLISS
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_scope import AuditScope
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


def test_covers_the_database_by_its_absolute_path_and_the_ids_and_the_mode() -> None:
    plan = AuditPlan(
        db="atlas.db", strict=BLISS, ids=StateIdRange(start=StateId(3), stop=StateId(9))
    )

    scope = AuditScope.of(plan)

    assert scope == AuditScope(
        db=str(Path("atlas.db").resolve()), mode="bliss", from_id=3, to_id=9
    )


def test_a_cheap_audit_of_every_id_has_no_mode_and_no_bounds() -> None:
    scope = AuditScope.of(AuditPlan(db="/data/atlas.db"))

    assert scope == AuditScope(db="/data/atlas.db", mode=None, from_id=None, to_id=None)
