import json
from pathlib import Path

import pytest

from booker.core.symmetry.state_symmetries import VF2
from booker.verify.audit_failure import AuditFailure
from booker.verify.checkpoint import BEFORE_ANY_ID, Checkpoint, Progress, Scope
from booker.verify.database import StateId
from booker.verify.plan import AuditPlan, IdRange


def _scope(path: Path, ids: IdRange | None = None) -> Scope:
    ids = IdRange() if ids is None else ids
    return Scope.of(AuditPlan(db=str(path / "atlas.db"), strict=VF2, ids=ids))


def test_a_whole_audit_starts_before_every_id() -> None:
    assert Progress.start(IdRange()) == Progress(
        next_id=BEFORE_ANY_ID, states=0, actions=0, pairings=0
    )


def test_a_ranged_audit_starts_at_its_range() -> None:
    assert Progress.start(IdRange(start=7)).next_id == 7


def test_progress_counts_what_each_state_brought() -> None:
    progress = Progress.start(IdRange()).after(StateId(value=4), actions=3, pairings=5)

    assert progress == Progress(next_id=5, states=1, actions=3, pairings=5)
    assert progress.after(StateId(value=9), 1, 1) == Progress(
        next_id=10, states=2, actions=4, pairings=6
    )


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
