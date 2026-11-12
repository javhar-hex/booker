"""
A read-only view of an atlas database, read row by row with SQL of its own rather than
through the `Atlas` that wrote it.
"""

from __future__ import annotations

import functools
import sqlite3
from collections.abc import Iterator
from types import TracebackType
from typing import Self

from javhar_util.immutables import ZMap, ZVec

from booker.verify.spot_check.action_row import ActionRow
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_row import StateRow

POSITION_CACHE_SIZE = 65536


class Database:
    def __init__(self, con: sqlite3.Connection) -> None:
        self._con = con
        self._load = functools.lru_cache(maxsize=POSITION_CACHE_SIZE)(self._read)

    @classmethod
    def open(cls, path: str) -> Database:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        con.execute("PRAGMA foreign_keys=ON")
        return cls(con)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._con.close()

    def metadata(self) -> ZMap[str, str]:
        return ZMap(dict(self._con.execute("SELECT key,value FROM meta")))

    def stored(self, state_id: StateId) -> StateRow:
        return self._load(state_id)

    def actions(self, parent: StateId) -> ZVec[ActionRow]:
        rows = self._con.execute(
            f"SELECT {ActionRow.COLUMNS} FROM actions WHERE parent=? ORDER BY lhs,rhs",
            (parent.value,),
        )
        return ZVec(ActionRow.of(row) for row in rows)

    def state_ids(self, start: int, stop: int | None) -> Iterator[StateId]:
        "The ids from `start` up to, not including, `stop`, in order."
        rows = self._con.execute(
            "SELECT id FROM states WHERE id>=? AND id<? ORDER BY id",
            (start, 2**62 if stop is None else stop),
        )
        for (state_id,) in rows:
            yield StateId(value=state_id)

    def schema_version(self) -> int:
        return self._count("PRAGMA user_version")

    def decided_ids(self) -> ZVec[StateId]:
        rows = self._con.execute("SELECT id FROM states WHERE active=1")
        return ZVec(StateId(value=state_id) for (state_id,) in rows)

    def num_unexpanded(self) -> int:
        return self._count("SELECT COUNT(*) FROM states WHERE expanded=0")

    def num_unvalued(self) -> int:
        return self._count(
            "SELECT (SELECT COUNT(*) FROM states WHERE value IS NULL)"
            "+(SELECT COUNT(*) FROM actions WHERE value IS NULL)"
        )

    def num_at_depth(self, depth: int) -> int:
        return self._count("SELECT COUNT(*) FROM states WHERE depth=?", (depth,))

    def max_depth(self) -> int:
        return self._count("SELECT MAX(depth) FROM states")

    def is_intact(self) -> bool:
        "SQLite's own integrity and foreign key checks both pass."
        ok = self._con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        return bool(ok and not self._con.execute("PRAGMA foreign_key_check").fetchone())

    def first_orphan(self, root: StateId) -> StateId | None:
        "A position that no action leads to, other than the root."
        row = self._con.execute(
            """
            SELECT s.id FROM states s WHERE s.id!=? AND NOT EXISTS (
              SELECT 1 FROM actions action WHERE action.lhs_wins=s.id OR action.rhs_wins=s.id
            ) LIMIT 1
            """,
            (root.value,),
        ).fetchone()
        return None if row is None else StateId(value=row[0])

    def _read(self, state_id: StateId) -> StateRow:
        row = self._con.execute(
            f"SELECT {StateRow.COLUMNS} FROM states WHERE id=?", (state_id.value,)
        ).fetchone()
        if row is None:
            raise AuditFailure(f"state {state_id.value} does not exist")
        return StateRow.of(state_id, row)

    def _count(self, sql: str, params: tuple[int, ...] = ()) -> int:
        count: int = self._con.execute(sql, params).fetchone()[0]
        return count
