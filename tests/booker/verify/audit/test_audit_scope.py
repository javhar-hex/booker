from pathlib import Path

from booker.core.symmetry.state_symmetries import BLISS
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_scope import AuditScope
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


def test_covers_the_database_by_its_path_and_the_ids_and_the_symmetry() -> None:
    plan = AuditPlan(
        db_path=Path("atlas.db"),
        reference_symmetry=BLISS,
        state_id_range=StateIdRange(start=StateId(3), stop=StateId(9)),
    )

    scope = AuditScope.of(plan)

    assert scope == AuditScope(
        db_path=Path("atlas.db").resolve(),
        reference_symmetry=BLISS,
        state_id_range=StateIdRange(start=StateId(3), stop=StateId(9)),
    )


def test_a_cheap_audit_of_every_id_has_no_symmetry_and_no_bounds() -> None:
    scope = AuditScope.of(AuditPlan(db_path=Path("/data/atlas.db")))

    assert scope == AuditScope(
        db_path=Path("/data/atlas.db"),
        reference_symmetry=None,
        state_id_range=StateIdRange(),
    )
