import json
from pathlib import Path

import pytest

from booker.core.symmetry.state_symmetries import VF2
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_scope import AuditScope
from booker.verify.audit.checkpoint import Checkpoint
from booker.verify.audit.progress import Progress
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


def _scope(path: Path, state_id_range: StateIdRange | None = None) -> AuditScope:
    state_id_range = StateIdRange() if state_id_range is None else state_id_range
    return AuditScope.of(
        AuditPlan(db_path=path / "atlas.db", strict=VF2, state_id_range=state_id_range)
    )


def test_a_missing_file_means_no_progress(tmp_path: Path) -> None:
    assert Checkpoint(tmp_path / "none.json", _scope(tmp_path)).load() is None


def test_saved_progress_is_loaded_again(tmp_path: Path) -> None:
    checkpoint = Checkpoint(tmp_path / "p.json", _scope(tmp_path))
    progress = Progress(
        next_id=StateId(value=12),
        states=11,
        counted=PairingCount(orbits=40, pairings=90),
    )

    checkpoint.save(progress)

    assert checkpoint.load() == progress


def test_progress_before_any_state_is_saved_and_loaded_again(tmp_path: Path) -> None:
    checkpoint = Checkpoint(tmp_path / "p.json", _scope(tmp_path))
    progress = Progress.start(StateIdRange())

    checkpoint.save(progress)

    assert checkpoint.load() == progress
    assert checkpoint.load() == Progress(
        next_id=None, states=0, counted=PairingCount.none()
    )


def test_saving_leaves_no_temporary_file(tmp_path: Path) -> None:
    Checkpoint(tmp_path / "p.json", _scope(tmp_path)).save(
        Progress(next_id=StateId(value=1), states=0, counted=PairingCount.none())
    )

    assert sorted(path.name for path in tmp_path.iterdir()) == ["p.json"]


def test_the_file_keeps_the_format_of_earlier_audits(tmp_path: Path) -> None:
    path = tmp_path / "p.json"
    Checkpoint(path, _scope(tmp_path, StateIdRange(start=StateId(3)))).save(
        Progress(
            next_id=StateId(value=4),
            states=1,
            counted=PairingCount(orbits=2, pairings=3),
        )
    )

    assert json.loads(path.read_text()) == {
        "scope": {
            "db": str(tmp_path / "atlas.db"),
            "mode": "vf2",
            "from_id": 3,
            "to_id": None,
        },
        "next_id": 4,
        "states": 1,
        "actions": 2,
        "pairings": 3,
    }


def test_progress_of_another_scope_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "p.json"
    Checkpoint(path, _scope(tmp_path)).save(Progress.start(StateIdRange()))

    with pytest.raises(AuditFailure, match="another run"):
        Checkpoint(path, _scope(tmp_path, StateIdRange(start=StateId(5)))).load()


def test_a_plan_without_a_checkpoint_has_none(tmp_path: Path) -> None:
    assert Checkpoint.of(AuditPlan(db_path=tmp_path / "atlas.db")) is None


def test_a_plan_with_a_checkpoint_has_it_for_its_own_scope(tmp_path: Path) -> None:
    plan = AuditPlan(
        db_path=tmp_path / "atlas.db",
        strict=VF2,
        state_id_range=StateIdRange(start=StateId(3)),
        checkpoint=tmp_path / "p.json",
    )

    assert Checkpoint.of(plan) == Checkpoint(
        tmp_path / "p.json", _scope(tmp_path, StateIdRange(start=StateId(3)))
    )
