"""
The audit walks the positions of an atlas and checks the atlas as a whole: the metadata,
the opening, completeness, orphans and the root GTV. The checks of one position are
shown in the tests of `StateCheck`. Whole-database checks are shown on a generated atlas.
"""

from pathlib import Path

import pytest
from support.hand_built_atlases import tampered_copy
from support.logs import discard

from booker.core.symmetry.state_symmetries import BLISS, VF2
from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.expand.atlas_expander import expand_atlas
from booker.verify.audit.audit import audit
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_report import AuditReport
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange

EVERY_STATE = StateIdRange(start=StateId(0))
ENDGAME_STATES = 29


def _audit(
    db_path: Path,
    state_id_range: StateIdRange = EVERY_STATE,
    limit: int | None = None,
    require_complete: bool = False,
    expected_root_gtv: int | None = None,
    checkpoint: Path | None = None,
    log: list[str] | None = None,
    strict: StateSymmetry | None = None,
) -> AuditReport:
    plan = AuditPlan(
        db_path=db_path,
        strict=strict,
        state_id_range=state_id_range,
        limit=limit,
        require_complete=require_complete,
        expected_root_gtv=expected_root_gtv,
        checkpoint=checkpoint,
    )
    return audit(plan, log=(log if log is not None else []).append)


def test_accepts_a_solved_atlas(solved: Path) -> None:
    report = _audit(solved)

    assert report.states == 2
    assert report.counted == PairingCount(orbits=1, pairings=1)
    assert report.is_solved
    assert report.unexpanded == 0


@pytest.mark.parametrize(
    ("sql", "complaint"),
    [
        ("PRAGMA user_version = 4", "schema"),
        ("UPDATE meta SET value='chess' WHERE key='game'", "game"),
        ("DELETE FROM meta WHERE key='root_id'", "does not say"),
    ],
)
def test_rejects_an_atlas_with_the_wrong_metadata(
    solved: Path, sql: str, complaint: str
) -> None:
    with pytest.raises(AuditFailure, match=complaint):
        _audit(tampered_copy(solved, sql))


def test_an_atlas_missing_a_gtv_is_audited_as_unsolved(solved: Path) -> None:
    report = _audit(tampered_copy(solved, "UPDATE states SET gtv=NULL WHERE id=1"))

    assert not report.is_solved


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("generated") / "atlas.db"
    expand_atlas(path, 4, BLISS, log=discard)
    return path


ORPHAN = "INSERT INTO states(key,depth,active,expanded) VALUES (X'010D', 31, 1, 1)"
ANOTHER_ROOT = (
    "INSERT INTO states(key,depth,active,expanded) "
    f"VALUES (X'10{'02' + '00' * 15}{'00' * 15}', 0, 16, 0)"
)
WRONG_OPENING = f"UPDATE states SET key=X'10{'02' + '00' * 15}{'00' * 15}' WHERE id=1"


def test_accepts_a_generated_atlas_as_a_whole(generated: Path) -> None:
    assert _audit(generated, state_id_range=StateIdRange()).states > 0


@pytest.mark.parametrize(
    ("sql", "complaint"),
    [
        (ORPHAN, "orphan state"),
        (ANOTHER_ROOT, "positions at depth 0"),
        (WRONG_OPENING, "wrong initial position"),
    ],
)
def test_rejects_a_generated_atlas_broken_as_a_whole(
    generated: Path, sql: str, complaint: str
) -> None:
    with pytest.raises(AuditFailure, match=complaint):
        _audit(tampered_copy(generated, sql), state_id_range=StateIdRange())


def test_a_ranged_audit_leaves_the_whole_database_checks_alone(generated: Path) -> None:
    _audit(
        tampered_copy(generated, ORPHAN),
        state_id_range=StateIdRange(start=StateId(1), stop=StateId(3)),
    )


def test_a_cut_short_audit_does_not_look_for_orphans(generated: Path) -> None:
    _audit(tampered_copy(generated, ORPHAN), state_id_range=StateIdRange(), limit=1)


def test_an_incomplete_atlas_is_refused_when_completeness_is_required(
    generated: Path,
) -> None:
    with pytest.raises(AuditFailure, match="not complete"):
        _audit(generated, state_id_range=StateIdRange(), require_complete=True)


def test_an_unsolved_root_is_not_the_expected_gtv(generated: Path) -> None:
    with pytest.raises(AuditFailure, match="root GTV is None, expected 3"):
        _audit(generated, state_id_range=StateIdRange(), expected_root_gtv=3)


def test_a_limit_stops_after_that_many_states(generated: Path) -> None:
    assert _audit(generated, state_id_range=StateIdRange(), limit=3).states == 3


def test_progress_is_logged_and_resumed(generated: Path, tmp_path: Path) -> None:
    checkpoint = tmp_path / "progress.json"
    first: list[str] = []
    second: list[str] = []

    _audit(
        generated,
        state_id_range=StateIdRange(),
        limit=3,
        checkpoint=checkpoint,
        log=first,
    )
    resumed = _audit(
        generated, state_id_range=StateIdRange(), checkpoint=checkpoint, log=second
    )

    assert first == []
    assert second == ["resuming at id 4 after 3 states"]
    assert resumed == _audit(generated, state_id_range=StateIdRange())


def test_accepts_the_rest_of_a_real_game(endgame: Path) -> None:
    report = _audit(endgame)

    assert report.states == ENDGAME_STATES
    assert report.is_solved
    assert report.unexpanded == 0


@pytest.mark.parametrize("symmetry", [BLISS, VF2])
def test_the_strict_audit_accepts_the_rest_of_a_real_game_with_any_implementation(
    endgame: Path, symmetry: StateSymmetry
) -> None:
    assert _audit(endgame, strict=symmetry).states == ENDGAME_STATES
