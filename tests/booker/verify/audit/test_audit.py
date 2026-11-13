"""
The audit walks the positions of an atlas and checks the atlas as a whole: the metadata,
the opening, completeness, orphans and the root GTV. The checks of one position are
shown in the tests of `StateCheck`. Whole-database checks are shown on a generated atlas.
"""

from pathlib import Path

import pytest
from support.hand_built_atlases import ORPHAN_STATE, tampered_copy

from booker.core.symmetry.state_symmetries import BLISS, VF2
from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.verify.audit.audit import audit
from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.audit_report import AuditReport
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange

EVERY_STATE = StateIdRange(start=StateId(0))
ENDGAME_STATES = 29


def _audit(
    db_path: Path,
    state_id_range: StateIdRange = EVERY_STATE,
    max_num_states: int | None = None,
    require_complete: bool = False,
    expected_root_gtv: int | None = None,
    checkpoint: Path | None = None,
    log: list[str] | None = None,
    reference_symmetry: StateSymmetry | None = None,
) -> AuditReport:
    plan = AuditPlan(
        db_path=db_path,
        reference_symmetry=reference_symmetry,
        state_id_range=state_id_range,
        max_num_states=max_num_states,
        require_complete=require_complete,
        expected_root_gtv=expected_root_gtv,
        checkpoint=checkpoint,
    )
    return audit(plan, log=(log if log is not None else []).append)


def test_accepts_a_solved_atlas(solved: Path) -> None:
    report = _audit(solved)

    assert report.num_checked_states == 2
    assert report.cml_pairing_count == PairingCount(orbits=1, pairings=1)
    assert report.is_solved
    assert report.num_unexpanded_states == 0


def test_an_atlas_missing_a_gtv_is_audited_as_unsolved(solved: Path) -> None:
    report = _audit(tampered_copy(solved, "UPDATE states SET gtv=NULL WHERE id=1"))

    assert not report.is_solved


def test_accepts_a_generated_atlas_as_a_whole(generated: Path) -> None:
    assert _audit(generated, state_id_range=StateIdRange()).num_checked_states > 0


def test_a_ranged_audit_leaves_the_whole_database_checks_alone(generated: Path) -> None:
    _audit(
        tampered_copy(generated, ORPHAN_STATE),
        state_id_range=StateIdRange(start=StateId(1), stop=StateId(3)),
    )


def test_a_limit_stops_after_that_many_states(generated: Path) -> None:
    assert (
        _audit(
            generated, state_id_range=StateIdRange(), max_num_states=3
        ).num_checked_states
        == 3
    )


def test_progress_is_logged_and_resumed(generated: Path, tmp_path: Path) -> None:
    checkpoint = tmp_path / "progress.json"
    first: list[str] = []
    second: list[str] = []

    _audit(
        generated,
        state_id_range=StateIdRange(),
        max_num_states=3,
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

    assert report.num_checked_states == ENDGAME_STATES
    assert report.is_solved
    assert report.num_unexpanded_states == 0


@pytest.mark.parametrize("symmetry", [BLISS, VF2])
def test_the_strict_audit_accepts_the_rest_of_a_real_game_with_any_implementation(
    endgame: Path, symmetry: StateSymmetry
) -> None:
    assert (
        _audit(endgame, reference_symmetry=symmetry).num_checked_states == ENDGAME_STATES
    )
