"""
What no single position shows: the metadata, the opening, completeness, orphans and the
root GTV, each broken in one way at a time.
"""

from pathlib import Path

import pytest
from support.hand_built_atlases import (
    ORPHAN_STATE,
    SECOND_ROOT_STATE,
    WRONG_ROOT_STATE,
    tampered_copy,
)

from booker.verify.audit.audit_plan import AuditPlan
from booker.verify.audit.global_check import GlobalCheck
from booker.verify.spot_check.atlas_reader import AtlasReader
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId


def _check_metadata(atlas: Path) -> None:
    with AtlasReader.open(atlas) as atlas_reader:
        GlobalCheck(atlas_reader).check_metadata()


def _check_whole_database(
    atlas: Path, require_complete: bool = False, max_num_states: int | None = None
) -> None:
    plan = AuditPlan(
        db_path=atlas.resolve(),
        require_complete=require_complete,
        max_num_states=max_num_states,
    )
    with AtlasReader.open(atlas) as atlas_reader:
        GlobalCheck(atlas_reader).check_whole_database(plan)


def _check_root_gtv(atlas: Path, expected_gtv: int) -> None:
    with AtlasReader.open(atlas) as atlas_reader:
        GlobalCheck(atlas_reader).check_root_gtv(expected_gtv)


def test_the_root_is_the_state_that_the_metadata_names(solved: Path) -> None:
    with AtlasReader.open(solved) as atlas_reader:
        root_id = atlas_reader.metadata()["root_id"]

        assert GlobalCheck(atlas_reader).root_state_id == StateId(value=int(root_id))


def test_accepts_the_metadata_of_a_solved_atlas(solved: Path) -> None:
    _check_metadata(solved)


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
        _check_metadata(tampered_copy(solved, sql))


def test_accepts_a_generated_atlas_as_a_whole(generated: Path) -> None:
    _check_whole_database(generated)


@pytest.mark.parametrize(
    ("sql", "complaint"),
    [
        (ORPHAN_STATE, "orphan state"),
        (SECOND_ROOT_STATE, "positions at depth 0"),
        (WRONG_ROOT_STATE, "wrong initial position"),
    ],
)
def test_rejects_a_generated_atlas_broken_as_a_whole(
    generated: Path, sql: str, complaint: str
) -> None:
    with pytest.raises(AuditFailure, match=complaint):
        _check_whole_database(tampered_copy(generated, sql))


def test_a_cut_short_audit_does_not_look_for_orphans(generated: Path) -> None:
    _check_whole_database(tampered_copy(generated, ORPHAN_STATE), max_num_states=1)


def test_an_incomplete_atlas_is_refused_when_completeness_is_required(
    generated: Path,
) -> None:
    with pytest.raises(AuditFailure, match="not complete"):
        _check_whole_database(generated, require_complete=True)


def test_a_complete_atlas_without_both_endings_is_refused(solved: Path) -> None:
    with pytest.raises(AuditFailure, match="incorrect leaf states"):
        _check_whole_database(solved, require_complete=True)


def test_a_complete_atlas_that_stops_short_of_the_last_match_is_refused(
    solved: Path,
) -> None:
    shortened = tampered_copy(solved, "UPDATE states SET depth=30")

    with pytest.raises(AuditFailure, match="last match is missing: depth 30"):
        _check_whole_database(shortened, require_complete=True)


def test_accepts_the_root_gtv_that_is_expected(solved: Path) -> None:
    with AtlasReader.open(solved) as atlas_reader:
        root_gtv = atlas_reader.state_row(GlobalCheck(atlas_reader).root_state_id).gtv
    assert root_gtv is not None

    _check_root_gtv(solved, root_gtv)
    with pytest.raises(AuditFailure, match=f"root GTV is {root_gtv}, expected 7"):
        _check_root_gtv(solved, 7)


def test_an_unsolved_root_is_not_the_expected_gtv(generated: Path) -> None:
    with pytest.raises(AuditFailure, match="root GTV is None, expected 3"):
        _check_root_gtv(generated, 3)
