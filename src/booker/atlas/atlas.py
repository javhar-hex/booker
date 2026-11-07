"""
An atlas, positions and the Scheduler's actions in SQLite, reached only through an
opened `Atlas`. Reading is done by the `Atlas` itself. Recording its expansion is done
through the `AtlasExpansionWriter` of `Atlas.transaction`, so that nothing is written
without being committed, and solving it through its `AtlasRetrogradeSolver`. The tables
are described in `booker.atlas.schema`.
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Self

from javhar_util.immutables import ZVec

from booker.atlas.atlas_expansion_writer import AtlasExpansionWriter
from booker.atlas.atlas_retrograde_solver import AtlasRetrogradeSolver
from booker.atlas.depth_summary import DepthSummary
from booker.atlas.packed_state import PackedState
from booker.atlas.schema import open_connection
from booker.atlas.state_id import StateId
from booker.atlas.stored_state import StoredState
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
    def transaction(self) -> Iterator[AtlasExpansionWriter]:
        with self._con:
            transaction = AtlasExpansionWriter(self._con)
            try:
                yield transaction
            finally:
                transaction.end()

    def retrograde_solver(self) -> AtlasRetrogradeSolver:
        return AtlasRetrogradeSolver(self._con)

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
