"""
The atlas as the generator and solver use it: positions and the Scheduler's actions
in SQLite, reached only through an opened `Atlas`. Reads and solving go through the
`Atlas` itself; every write goes through the `AtlasTransaction` of `Atlas.transaction`,
so nothing is ever written without being committed. The tables are in `booker.atlas.schema`.
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Self

from javhar_util.immutables import ZVec

from booker.atlas.codec import PackedState
from booker.atlas.schema import open_connection
from booker.atlas.stored import DepthSummary, StateId, StoredState
from booker.atlas.transaction import AtlasTransaction
from booker.core.model.state import State


class Atlas:
    "An open atlas database. Obtain one with `Atlas.open`."

    def __init__(self, con: sqlite3.Connection) -> None:
        self._con = con

    @classmethod
    def open(cls, path: str | Path) -> Atlas:
        return cls(open_connection(path))

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._con.close()

    @contextlib.contextmanager
    def transaction(self) -> Iterator[AtlasTransaction]:
        with self._con:
            yield AtlasTransaction(self._con)

    def state(self, state_id: StateId) -> State:
        row = self._con.execute(
            "SELECT key FROM states WHERE id=?", (state_id.value,)
        ).fetchone()
        if row is None:
            raise KeyError(state_id)
        return PackedState(data=row[0]).state

    def states(self) -> Iterator[State]:
        for (data,) in self._con.execute("SELECT key FROM states"):
            yield PackedState(data=data).state

    def unexpanded(self, depth: int) -> ZVec[StoredState]:
        rows = self._con.execute(
            "SELECT id,key FROM states WHERE depth=? AND expanded=0 ORDER BY id",
            (depth,),
        )
        return ZVec(
            StoredState(id=StateId(value=sid), state=PackedState(data=data).state)
            for sid, data in rows
        )

    def num_states(self) -> int:
        return self._count("SELECT COUNT(*) FROM states")

    def num_actions(self) -> int:
        return self._count("SELECT COUNT(*) FROM actions")

    def num_unexpanded(self) -> int:
        return self._count("SELECT COUNT(*) FROM states WHERE expanded=0")

    def reset_values(self) -> None:
        "Forget every value but the decided positions', which are worth nothing more."
        with self._con:
            self._con.execute("UPDATE actions SET value=NULL")
            self._con.execute("UPDATE states SET value=NULL")
            self._con.execute("UPDATE states SET value=0 WHERE active=1")

    def back_up(self, depth: int) -> None:
        "Values the positions at `depth` from their children, which are at `depth + 1`."
        with self._con:
            self._con.execute(
                """
                UPDATE actions SET value=(
                  SELECT MAX(c1.value,c2.value) FROM states c1, states c2
                  WHERE c1.id=actions.a_wins AND c2.id=actions.b_wins
                ) WHERE parent IN (SELECT id FROM states WHERE depth=?)
                """,
                (depth,),
            )
            self._con.execute(
                """
                UPDATE states SET value=(
                  SELECT MIN(repeat_cost + value) FROM actions WHERE parent=states.id
                ) WHERE depth=? AND active>1
                """,
                (depth,),
            )

    def num_unvalued(self, depth: int) -> int:
        return self._count(
            """
            SELECT (SELECT COUNT(*) FROM states WHERE depth=?1 AND value IS NULL)
                 + (SELECT COUNT(*) FROM actions WHERE value IS NULL
                    AND parent IN (SELECT id FROM states WHERE depth=?1))
            """,
            (depth,),
        )

    def mark_solved(self) -> None:
        with self._con:
            self._con.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES ('solved','true')"
            )

    def root_value(self) -> int:
        row = self._con.execute(
            "SELECT value FROM states WHERE id="
            "(SELECT CAST(value AS INTEGER) FROM meta WHERE key='root_id')"
        ).fetchone()
        if row is None or row[0] is None:
            raise ValueError("the atlas has no solved root")
        value: int = row[0]
        return value

    def depth_summaries(self) -> Iterator[DepthSummary]:
        rows = self._con.execute("""
            SELECT s.depth, COUNT(DISTINCT s.id), COUNT(a.a),
                   COALESCE(SUM(a.class_size),0), MIN(s.value), MAX(s.value)
            FROM states s LEFT JOIN actions a ON a.parent=s.id
            GROUP BY s.depth ORDER BY s.depth
            """)
        for depth, states, colliders, pairings, lowest, highest in rows:
            yield DepthSummary(
                depth=depth,
                num_states=states,
                num_colliders=colliders,
                num_pairings=pairings,
                min_value=lowest,
                max_value=highest,
            )

    def _count(self, sql: str, params: tuple[int, ...] = ()) -> int:
        count: int = self._con.execute(sql, params).fetchone()[0]
        return count
