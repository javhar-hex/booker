"""
A read-only view of an atlas database, read row by row with SQL of its own rather than
through the `Atlas` that wrote it.
"""

from __future__ import annotations

import functools
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Self

from javhar_util.immutables import ZMap, ZVec

from booker.verify.spot_check.action_row import ActionRow
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange
from booker.verify.spot_check.state_row import StateRow

POSITION_CACHE_SIZE = 65536


class AtlasReader:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._read_cached = functools.lru_cache(maxsize=POSITION_CACHE_SIZE)(
            self._read_uncached
        )

    @classmethod
    def open(cls, path: Path) -> AtlasReader:
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        connection.execute("PRAGMA foreign_keys=ON")
        return cls(connection)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        _exception_type: type[BaseException] | None,
        _exception: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self._connection.close()

    def metadata(self) -> ZMap[str, str]:
        return ZMap(dict(self._connection.execute("SELECT key,value FROM meta")))

    def state_row(self, state_id: StateId) -> StateRow:
        return self._read_cached(state_id)

    def action_rows(self, parent: StateId) -> ZVec[ActionRow]:
        rows = self._connection.execute(
            f"SELECT {ActionRow.COLUMNS} FROM actions WHERE parent=? ORDER BY lhs,rhs",
            (parent.value,),
        )
        return ZVec(ActionRow.of(row) for row in rows)

    def state_ids(self, id_range: StateIdRange) -> Iterator[StateId]:
        "The ids in `id_range`, in order."
        start = None if id_range.start is None else id_range.start.value
        stop = None if id_range.stop is None else id_range.stop.value
        # SQLite cannot use a bound inside an OR to search the rowids, so a range scans
        # from the first row to the last, and filters. A flag per bound keeps one query.
        rows = self._connection.execute(
            "SELECT id FROM states WHERE (? OR id>=?) AND (? OR id<?) ORDER BY id",
            (start is None, start, stop is None, stop),
        )
        for (state_id,) in rows:
            yield StateId(value=state_id)

    def schema_version(self) -> int:
        return self._count("PRAGMA user_version")

    def leaf_ids(self) -> ZVec[StateId]:
        rows = self._connection.execute("SELECT id FROM states WHERE active=1")
        return ZVec(StateId(value=state_id) for (state_id,) in rows)

    def num_unexpanded(self) -> int:
        return self._count("SELECT COUNT(*) FROM states WHERE expanded=0")

    def num_unsolved(self) -> int:
        return self._count(
            "SELECT (SELECT COUNT(*) FROM states WHERE gtv IS NULL)"
            "+(SELECT COUNT(*) FROM actions WHERE gtv IS NULL)"
        )

    def num_at_depth(self, depth: int) -> int:
        return self._count("SELECT COUNT(*) FROM states WHERE depth=?", (depth,))

    def max_depth(self) -> int:
        return self._count("SELECT MAX(depth) FROM states")

    def is_intact(self) -> bool:
        "SQLite's own integrity and foreign key checks both pass."
        return (
            self._connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            and self._connection.execute("PRAGMA foreign_key_check").fetchone() is None
        )

    def first_orphan(self, root: StateId) -> StateId | None:
        "A position that no action leads to, other than the root."
        row = self._connection.execute(
            """
            SELECT s.id FROM states s WHERE s.id!=? AND NOT EXISTS (
              SELECT 1 FROM actions action WHERE action.lhs_wins=s.id OR action.rhs_wins=s.id
            ) LIMIT 1
            """,
            (root.value,),
        ).fetchone()
        return None if row is None else StateId(value=row[0])

    def _read_uncached(self, state_id: StateId) -> StateRow:
        row = self._connection.execute(
            f"SELECT {StateRow.COLUMNS} FROM states WHERE id=?", (state_id.value,)
        ).fetchone()
        if row is None:
            raise AuditFailure.of(state_id, "does not exist")
        return StateRow.of(state_id, row)

    def _count(self, sql: str, params: tuple[int, ...] = ()) -> int:
        count: int = self._connection.execute(sql, params).fetchone()[0]
        return count
