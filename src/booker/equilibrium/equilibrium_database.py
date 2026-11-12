"""The equilibrium database, with the atlas it analyzes attached to it, read-only."""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Self

from javhar_util.immutables import ZVec

from booker.atlas.schema import SCHEMA_VERSION
from booker.equilibrium.layer_summary import LayerSummary
from booker.equilibrium.sql import COLLIDER_LAYER, SCHEDULER_LAYER, SCHEMA, SUMMARY


class EquilibriumDatabase:
    "Obtain one with `EquilibriumDatabase.open`."

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @classmethod
    def open(cls, atlas: Path, analysis: Path) -> EquilibriumDatabase:
        "`analysis` is created if it is new; `atlas` is never written to, nor its schema guessed."
        # URIs, not paths, so that `mode=ro` is honoured whichever way SQLite was built.
        connection = sqlite3.connect(analysis.resolve().as_uri(), uri=True)
        try:
            attached = f"{atlas.resolve().as_uri()}?mode=ro"
            connection.execute("ATTACH DATABASE ? AS atlas", (attached,))
            database = cls(connection)
            database._require_this_schema()
        except BaseException:
            connection.close()
            raise
        return database

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._connection.close()

    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        with self._connection:
            yield

    def require_solved(self) -> None:
        solved = self._connection.execute(
            "SELECT value FROM atlas.meta WHERE key='solved'"
        ).fetchone()
        unvalued = self._connection.execute(
            "SELECT (SELECT COUNT(*) FROM atlas.states WHERE value IS NULL)"
            " + (SELECT COUNT(*) FROM atlas.actions WHERE value IS NULL)"
        ).fetchone()[0]
        if solved is None or solved[0] != "true":
            raise ValueError("Atlas is not solved: it has not been through `solve`")
        if unvalued:
            raise ValueError(
                f"Atlas is not solved: {unvalued:,} positions without a value"
            )

    def create_tables(self) -> None:
        self._connection.executescript(SCHEMA)

    def analyze_root(self) -> None:
        self._connection.execute(
            "INSERT INTO scheduler_equilibrium VALUES (?, 1, 0)", (self._root_id(),)
        )

    def analyze_depth(self, depth: int) -> None:
        "Analyzes the Collider positions under the Scheduler's at `depth`, then their children."
        self._connection.execute(COLLIDER_LAYER, (depth,))
        self._connection.execute(SCHEDULER_LAYER, (depth,))

    def max_depth(self) -> int:
        depth: int = self._connection.execute(
            "SELECT MAX(depth) FROM atlas.states"
        ).fetchone()[0]
        return depth

    def require_every_state_analyzed(self) -> None:
        missing = self._connection.execute(
            "SELECT COUNT(*) FROM atlas.states state WHERE NOT EXISTS"
            " (SELECT 1 FROM scheduler_equilibrium"
            " WHERE scheduler_equilibrium.id = state.id)"
        ).fetchone()[0]
        if missing:
            raise RuntimeError(f"{missing:,} states were never reached from the root")

    def layer_summaries(self) -> ZVec[LayerSummary]:
        rows = self._connection.execute(SUMMARY, (self._root_value(),)).fetchall()
        return ZVec(
            LayerSummary(
                depth=depth,
                scheduler=scheduler,
                scheduler_equilibrium=scheduler_equilibrium,
                scheduler_balanced_off_equilibrium=balanced_off,
                collider=collider,
                collider_equilibrium=collider_equilibrium,
                collider_critical=collider_critical,
            )
            for (
                depth,
                scheduler,
                scheduler_equilibrium,
                balanced_off,
                collider,
                collider_equilibrium,
                collider_critical,
            ) in rows
        )

    def _require_this_schema(self) -> None:
        version = self._connection.execute("PRAGMA atlas.user_version").fetchone()[0]
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"Atlas has schema v{version}, "
                f"but the equilibrium pass reads v{SCHEMA_VERSION}"
            )

    def _root_id(self) -> int:
        row = self._connection.execute(
            "SELECT value FROM atlas.meta WHERE key='root_id'"
        ).fetchone()
        return int(row[0])

    def _root_value(self) -> int:
        row = self._connection.execute(
            "SELECT value FROM atlas.states WHERE id = ?", (self._root_id(),)
        ).fetchone()
        return int(row[0])
