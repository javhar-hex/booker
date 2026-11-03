"""
Each check of the verifier is shown to fire: a small, hand-built and fully solved atlas
is accepted, and then broken in one way at a time. Whole-database checks are shown on a
generated atlas.
"""

import shutil
import sqlite3
from pathlib import Path

import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.atlas.storage import Atlas
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.generate.backend import BLISS
from booker.generate.generator import generate
from booker.verify.audit import audit
from booker.verify.failure import AuditFailure
from booker.verify.isomorphism import NETWORKX
from booker.verify.plan import AuditPlan, AuditReport, IdRange

PAIRING = Pairing.of(Team(index=0), Team(index=1))
FINAL = Record(wins=5, losses=1)
CHAMPION = Record(wins=6, losses=1)
SURVIVOR = Record(wins=4, losses=1)
EVERY_STATE = IdRange(start=0)
PARENT, CHILD = 1, 2


def _state(*records: Record, met: bool = False) -> State:
    return State(records=ZVec(records), met=ZSet([PAIRING] if met else []))


def _build(
    path: Path,
    parent: State,
    children: tuple[State, State],
    pairing: Pairing | None,
    is_rematch: bool = False,
) -> Path:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            parent_id = tx.add_state(parent)
            low, high = (tx.add_state(child) for child in children)
            tx.record_root(parent_id)
            if pairing is not None:
                tx.add_action(parent_id, pairing, is_rematch, 1, low, high)
            tx.mark_expanded(parent_id)
            tx.mark_decided_expanded()
        atlas.reset_values()
        for depth in range(MAX_MATCHES, -1, -1):
            atlas.back_up(depth)
    return path


def _final_pair(path: Path, met: bool = False) -> Path:
    "Two teams a loss from elimination: whoever wins the match is the champion."
    champion = _state(CHAMPION)
    return _build(
        path, _state(FINAL, FINAL, met=met), (champion, champion), PAIRING, met
    )


def _audit(
    db: Path,
    ids: IdRange = EVERY_STATE,
    limit: int | None = None,
    require_complete: bool = False,
    expect_root: int | None = None,
    checkpoint: Path | None = None,
    log: list[str] | None = None,
) -> AuditReport:
    plan = AuditPlan(
        db=str(db),
        mode=NETWORKX,
        ids=ids,
        limit=limit,
        require_complete=require_complete,
        expect_root=expect_root,
        checkpoint=None if checkpoint is None else str(checkpoint),
    )
    return audit(plan, log=(log if log is not None else []).append)


def _tamper(db: Path, sql: str) -> Path:
    tampered = db.with_name("tampered.db")
    shutil.copy(db, tampered)
    con = sqlite3.connect(tampered)
    with con:
        con.execute(sql)
    con.close()
    return tampered


@pytest.fixture
def solved(tmp_path: Path) -> Path:
    return _final_pair(tmp_path / "solved.db")


def test_accepts_a_solved_atlas(solved: Path) -> None:
    report = _audit(solved)

    assert (report.states, report.actions, report.pairings) == (2, 1, 1)
    assert report.is_solved
    assert report.unexpanded == 0


def test_accepts_a_rematch_that_costs_one(tmp_path: Path) -> None:
    assert _audit(_final_pair(tmp_path / "rematch.db", met=True)).is_solved


@pytest.mark.parametrize(
    ("sql", "ids", "complaint"),
    [
        ("UPDATE states SET value=5 WHERE id=1", EVERY_STATE, "best action is worth"),
        ("UPDATE actions SET value=3", EVERY_STATE, "Collider value"),
        ("UPDATE actions SET repeat_cost=1", EVERY_STATE, "wrong repeat cost"),
        ("UPDATE actions SET a_wins=1", EVERY_STATE, "wrong state"),
        ("UPDATE actions SET a_wins=99", EVERY_STATE, "does not exist"),
        ("UPDATE states SET expanded=0 WHERE id=1", EVERY_STATE, "unexpanded, with"),
        ("UPDATE states SET expanded=0 WHERE id=2", EVERY_STATE, "bad decided state"),
        ("UPDATE states SET value=1 WHERE id=2", IdRange(start=CHILD), "worth 0"),
        ("UPDATE states SET depth=29 WHERE id=2", IdRange(start=CHILD), "depth 29"),
        ("UPDATE states SET active=3 WHERE id=1", EVERY_STATE, "team count"),
        ("UPDATE states SET key=X'FF' WHERE id=2", IdRange(start=CHILD), "claims 255"),
        ("UPDATE meta SET value='4' WHERE key='schema_version'", EVERY_STATE, "schema"),
        ("UPDATE meta SET value='chess' WHERE key='game'", EVERY_STATE, "game"),
        ("DELETE FROM meta WHERE key='root_id'", EVERY_STATE, "does not say"),
    ],
)
def test_rejects_a_solved_atlas_broken_in_one_way(
    solved: Path, sql: str, ids: IdRange, complaint: str
) -> None:
    with pytest.raises(AuditFailure, match=complaint):
        _audit(_tamper(solved, sql), ids=ids)


@pytest.mark.parametrize(
    ("key", "depth", "complaint"),
    [
        ("020000 01", 28, "unbeaten teams have met"),
        ("020D0200", 29, "a champion, with teams still playing"),
    ],
)
def test_rejects_an_impossible_position(
    solved: Path, key: str, depth: int, complaint: str
) -> None:
    sql = (
        "INSERT INTO states(key,depth,active,expanded,value) "
        f"VALUES (X'{key.replace(' ', '')}', {depth}, 2, 0, 0)"
    )

    with pytest.raises(AuditFailure, match=complaint):
        _audit(_tamper(solved, sql), ids=IdRange(start=3))


def test_an_atlas_missing_a_value_is_audited_as_unsolved(solved: Path) -> None:
    report = _audit(_tamper(solved, "UPDATE states SET value=NULL WHERE id=1"))

    assert not report.is_solved


def test_rejects_an_illegal_pairing(tmp_path: Path) -> None:
    parent = _state(FINAL, SURVIVOR)
    atlas = _build(
        tmp_path / "illegal.db",
        parent,
        (_state(CHAMPION), _state(FINAL)),
        PAIRING,
    )

    with pytest.raises(AuditFailure, match="illegal pairings"):
        _audit(atlas)


def test_rejects_a_dead_end(tmp_path: Path) -> None:
    atlas = _build(
        tmp_path / "dead.db",
        _state(FINAL, SURVIVOR),
        (_state(CHAMPION), _state(CHAMPION)),
        pairing=None,
    )

    with pytest.raises(AuditFailure, match="dead end"):
        _audit(atlas)


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("generated") / "atlas.db"
    generate(str(path), 4, BLISS)
    return path


ORPHAN = "INSERT INTO states(key,depth,active,expanded) VALUES (X'010D', 31, 1, 1)"
ANOTHER_ROOT = (
    "INSERT INTO states(key,depth,active,expanded) "
    f"VALUES (X'10{'02' + '00' * 15}{'00' * 15}', 0, 16, 0)"
)
WRONG_OPENING = f"UPDATE states SET key=X'10{'02' + '00' * 15}{'00' * 15}' WHERE id=1"


def test_accepts_a_generated_atlas_as_a_whole(generated: Path) -> None:
    assert _audit(generated, ids=IdRange()).states > 0


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
        _audit(_tamper(generated, sql), ids=IdRange())


def test_a_ranged_audit_leaves_the_whole_database_checks_alone(generated: Path) -> None:
    _audit(_tamper(generated, ORPHAN), ids=IdRange(start=1, stop=3))


def test_a_cut_short_audit_does_not_look_for_orphans(generated: Path) -> None:
    _audit(_tamper(generated, ORPHAN), ids=IdRange(), limit=1)


def test_an_incomplete_atlas_is_refused_when_completeness_is_required(
    generated: Path,
) -> None:
    with pytest.raises(AuditFailure, match="not complete"):
        _audit(generated, ids=IdRange(), require_complete=True)


def test_an_unsolved_root_is_not_the_expected_value(generated: Path) -> None:
    with pytest.raises(AuditFailure, match="root value is None, expected 3"):
        _audit(generated, ids=IdRange(), expect_root=3)


def test_a_limit_stops_after_that_many_states(generated: Path) -> None:
    assert _audit(generated, ids=IdRange(), limit=3).states == 3


def test_progress_is_logged_and_resumed(generated: Path, tmp_path: Path) -> None:
    checkpoint = tmp_path / "progress.json"
    first: list[str] = []
    second: list[str] = []

    _audit(generated, ids=IdRange(), limit=3, checkpoint=checkpoint, log=first)
    resumed = _audit(generated, ids=IdRange(), checkpoint=checkpoint, log=second)

    assert first == []
    assert second == ["resuming at id 4 after 3 states"]
    assert resumed == _audit(generated, ids=IdRange())
