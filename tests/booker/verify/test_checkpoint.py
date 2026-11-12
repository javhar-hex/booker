import json
from pathlib import Path

import pytest

from booker.core.symmetry.state_symmetries import VF2
from booker.verify.audit_failure import AuditFailure
from booker.verify.audit_plan import AuditPlan
from booker.verify.checkpoint import Checkpoint
from booker.verify.id_range import IdRange
from booker.verify.progress import Progress


def _scope(path: Path, ids: IdRange | None = None) -> Checkpoint.Scope:
    ids = IdRange() if ids is None else ids
    return Checkpoint.Scope.of(AuditPlan(db=str(path / "atlas.db"), strict=VF2, ids=ids))


def test_a_missing_file_means_no_progress(tmp_path: Path) -> None:
    assert Checkpoint(str(tmp_path / "none.json"), _scope(tmp_path)).load() is None


def test_saved_progress_is_loaded_again(tmp_path: Path) -> None:
    checkpoint = Checkpoint(str(tmp_path / "p.json"), _scope(tmp_path))
    progress = Progress(next_id=12, states=11, actions=40, pairings=90)

    checkpoint.save(progress)

    assert checkpoint.load() == progress


def test_saving_leaves_no_temporary_file(tmp_path: Path) -> None:
    Checkpoint(str(tmp_path / "p.json"), _scope(tmp_path)).save(
        Progress(next_id=1, states=0, actions=0, pairings=0)
    )

    assert sorted(path.name for path in tmp_path.iterdir()) == ["p.json"]


def test_the_file_keeps_the_format_of_earlier_audits(tmp_path: Path) -> None:
    path = tmp_path / "p.json"
    Checkpoint(str(path), _scope(tmp_path, IdRange(start=3))).save(
        Progress(next_id=4, states=1, actions=2, pairings=3)
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
    path = str(tmp_path / "p.json")
    Checkpoint(path, _scope(tmp_path)).save(Progress.start(IdRange()))

    with pytest.raises(AuditFailure, match="another run"):
        Checkpoint(path, _scope(tmp_path, IdRange(start=5))).load()


def test_a_plan_without_a_checkpoint_has_none(tmp_path: Path) -> None:
    assert Checkpoint.of(AuditPlan(db=str(tmp_path / "atlas.db"))) is None


def test_a_plan_with_a_checkpoint_has_it_for_its_own_scope(tmp_path: Path) -> None:
    plan = AuditPlan(
        db=str(tmp_path / "atlas.db"),
        strict=VF2,
        ids=IdRange(start=3),
        checkpoint=str(tmp_path / "p.json"),
    )

    assert Checkpoint.of(plan) == Checkpoint(
        str(tmp_path / "p.json"), _scope(tmp_path, IdRange(start=3))
    )
