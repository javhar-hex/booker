"""
An atlas, positions and the Scheduler's actions in SQLite, reached only through an
opened `Atlas`. Reading is done by the `Atlas` itself. Writing a generation is done
through the `AtlasWriter` of `Atlas.transaction`, so that nothing is written without
being committed, and valuing it through its `AtlasValuation`. The tables are described
in `booker.atlas.schema`.
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Self

from javhar_util.immutables import ZVec

from booker.atlas.atlas_valuation import AtlasValuation
from booker.atlas.atlas_writer import AtlasWriter
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
    def transaction(self) -> Iterator[AtlasWriter]:
        with self._con:
            transaction = AtlasWriter(self._con)
            try:
                yield transaction
            finally:
                transaction.end()

    def valuation(self) -> AtlasValuation:
        return AtlasValuation(self._con)

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

    def _count(self, sql: str, params: tuple[int, ...] = ()) -> int:
        count: int = self._con.execute(sql, params).fetchone()[0]
        return count
