"""The checks on the atlas as a whole, rather than on one position."""

from __future__ import annotations

from booker.atlas.schema import META, SCHEMA_VERSION
from booker.core.model.invariants import (
    CHAMPION_WINS,
    ELIMINATION_LOSSES,
    MAX_MATCHES,
    NUM_PARTICIPANTS,
)
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.verify.audit_failure import AuditFailure
from booker.verify.audit_plan import AuditPlan
from booker.verify.database import Database
from booker.verify.state_id import StateId


def check_metadata(db: Database) -> StateId:
    "The atlas is of this game and schema; returns the id of its root."
    metadata = db.metadata()
    if db.schema_version() != SCHEMA_VERSION:
        raise AuditFailure(f"schema version {db.schema_version()}, not {SCHEMA_VERSION}")
    if metadata.get("game") != META["game"]:
        raise AuditFailure(f"game {metadata.get('game')}, not {META['game']}")
    root = metadata.get("root_id")
    if root is None:
        raise AuditFailure("the atlas does not say which position is its root")
    return StateId(value=int(root))


def check_whole_database(db: Database, plan: AuditPlan, root: StateId) -> None:
    if plan.require_complete:
        _check_complete(db)
    _check_opening(db, root)
    # A depth-increasing DAG whose only source is the root is rooted wholly there,
    # which rules out extra, disconnected positions. Cut short, the walk is partial.
    if plan.limit is None and (orphan := db.first_orphan(root)) is not None:
        raise AuditFailure(f"orphan state {orphan.value}: no action leads to it")


def check_root_value(db: Database, root: StateId, expected: int) -> None:
    value = db.stored(root).value
    if value != expected:
        raise AuditFailure(f"root value is {value}, expected {expected}")


def _check_complete(db: Database) -> None:
    unexpanded, unvalued = db.num_unexpanded(), db.num_unvalued()
    if unexpanded or unvalued:
        raise AuditFailure(
            f"not complete: {unexpanded:,} unexpanded states, {unvalued:,} without a value"
        )
    if db.max_depth() != MAX_MATCHES:
        raise AuditFailure(f"last match is missing: depth {db.max_depth()}")
    decided = {
        (stored.state.records[0], stored.depth)
        for stored in (db.stored(state_id) for state_id in db.decided_ids())
    }
    if len(db.decided_ids()) != 2 or decided != _both_endings():
        raise AuditFailure(f"incorrect decided states: {sorted(map(str, decided))}")


def _both_endings() -> set[tuple[Record, int]]:
    "The champion wins CHAMPION_WINS matches, and loses none or all but one life."
    first_ending = ELIMINATION_LOSSES * (NUM_PARTICIPANTS - 1)
    return {
        (Record(wins=CHAMPION_WINS, losses=losses), first_ending + losses)
        for losses in (0, ELIMINATION_LOSSES - 1)
    }


def _check_opening(db: Database, root: StateId) -> None:
    if db.stored(root).state != State.start():
        raise AuditFailure("wrong initial position")
    if db.num_at_depth(0) != 1:
        raise AuditFailure(f"{db.num_at_depth(0)} positions at depth 0, expected 1")
    if not db.is_intact():
        raise AuditFailure("SQLite integrity or foreign key check failed")
