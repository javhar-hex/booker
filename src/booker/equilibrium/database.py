"""The flags database, with the atlas it flags attached to it, read-only."""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Self

from javhar_util.immutables import ZVec

from booker.atlas.schema import SCHEMA_VERSION
from booker.equilibrium.layers import LayerSummary
from booker.equilibrium.sql import COLLIDER_LAYER, SCHEDULER_LAYER, SCHEMA, SUMMARY


class FlagsDatabase:
    "Obtain one with `FlagsDatabase.open`."

    def __init__(self, con: sqlite3.Connection) -> None:
        self._con = con

    @classmethod
    def open(cls, atlas: Path, flags: Path) -> FlagsDatabase:
        "`flags` is created if it is new; `atlas` is never written to, nor its schema guessed."
        # URIs, not paths, so that `mode=ro` is honoured whichever way SQLite was built.
        con = sqlite3.connect(flags.resolve().as_uri(), uri=True)
        try:
            attached = f"{atlas.resolve().as_uri()}?mode=ro"
            con.execute("ATTACH DATABASE ? AS atlas", (attached,))
            database = cls(con)
            database._require_this_schema()
        except BaseException:
            con.close()
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
        self._con.close()

    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        with self._con:
            yield

    def require_solved(self) -> None:
        solved = self._con.execute(
            "SELECT value FROM atlas.meta WHERE key='solved'"
        ).fetchone()
        unvalued = self._con.execute(
            "SELECT (SELECT COUNT(*) FROM atlas.states WHERE value IS NULL)"
            " + (SELECT COUNT(*) FROM atlas.actions WHERE value IS NULL)"
        ).fetchone()[0]
        if solved is None or solved[0] != "true":
            raise ValueError("Atlas is not solved: it has not been through `solve`")
        if unvalued:
            raise ValueError(
                f"Atlas is not solved: {unvalued:,} positions without a value"
            )

    def create_flag_tables(self) -> None:
        self._con.executescript(SCHEMA)

    def flag_root(self) -> None:
        self._con.execute(
            "INSERT INTO scheduler_flags VALUES (?, 1, 0)", (self._root_id(),)
        )

    def flag_depth(self, depth: int) -> None:
        "Flags the Collider positions under the Scheduler's at `depth`, then their children."
        self._con.execute(COLLIDER_LAYER, (depth,))
        self._con.execute(SCHEDULER_LAYER, (depth,))

    def max_depth(self) -> int:
        depth: int = self._con.execute("SELECT MAX(depth) FROM atlas.states").fetchone()[
            0
        ]
        return depth

    def require_every_state_flagged(self) -> None:
        missing = self._con.execute(
            "SELECT COUNT(*) FROM atlas.states s"
            " WHERE NOT EXISTS (SELECT 1 FROM scheduler_flags f WHERE f.id = s.id)"
        ).fetchone()[0]
        if missing:
            raise RuntimeError(f"{missing:,} states were never reached from the root")

    def layers(self) -> ZVec[LayerSummary]:
        rows = self._con.execute(SUMMARY, (self._root_value(),)).fetchall()
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
        row = self._con.execute(
            "SELECT value FROM atlas.meta WHERE key='schema_version'"
        ).fetchone()
        if row is None or row[0] != SCHEMA_VERSION:
            raise ValueError(
                f"Atlas has schema {None if row is None else 'v' + row[0]}, "
                f"but the equilibrium pass reads v{SCHEMA_VERSION}"
            )

    def _root_id(self) -> int:
        row = self._con.execute(
            "SELECT value FROM atlas.meta WHERE key='root_id'"
        ).fetchone()
        return int(row[0])

    def _root_value(self) -> int:
        row = self._con.execute(
            "SELECT value FROM atlas.states WHERE id = ?", (self._root_id(),)
        ).fetchone()
        return int(row[0])
