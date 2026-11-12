"""
Equilibrium analysis of a solved atlas, written to a separate database.

- equilibrium: reachable from the root when both players only make optimal moves.
- critical (Collider positions): an equilibrium position where one winner is a mistake.
- fewest_past_repeats: the fewest repeats over all paths from the root. A position is
  balanced when this plus its value equals the root value; off the equilibrium path,
  that means it is only reachable through mistakes that cancel each other out.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import Self

from javhar_util.immutables import ZVec

from booker.atlas.schema import SCHEMA_VERSION
from booker.equilibrium.layer_summary import LayerSummary
from booker.equilibrium.sql import COLLIDER_LAYER, SCHEDULER_LAYER, SCHEMA, SUMMARY


class EquilibriumAnalysis:
    """
    The equilibrium analysis of a solved atlas, in a database of its own with the atlas
    attached to it, read-only. Obtain one with `EquilibriumAnalysis.open`.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @classmethod
    def open(cls, atlas: Path, analysis: Path) -> EquilibriumAnalysis:
        "`analysis` is created if it is new; `atlas` is never written to, nor its schema guessed."
        # URIs, not paths, so that `mode=ro` is honoured whichever way SQLite was built.
        # Autocommit: the analysis is atomic as a file, by being renamed once complete.
        connection = sqlite3.connect(
            analysis.resolve().as_uri(), uri=True, isolation_level=None
        )
        try:
            attached = f"{atlas.resolve().as_uri()}?mode=ro"
            connection.execute("ATTACH DATABASE ? AS atlas", (attached,))
            equilibrium_analysis = cls(connection)
            equilibrium_analysis._require_this_schema()
        except BaseException:
            connection.close()
            raise
        return equilibrium_analysis

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._connection.close()

    def analyze(self) -> None:
        "Analyzes every position of the atlas, which must be solved, from the root down."
        self._require_solved()
        self._connection.executescript(SCHEMA)
        self._analyze_root()
        for depth in range(self._max_depth()):
            self._analyze_depth(depth)
        self._require_every_state_analyzed()

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

    def _require_solved(self) -> None:
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

    def _analyze_root(self) -> None:
        self._connection.execute(
            "INSERT INTO scheduler_equilibrium VALUES (?, 1, 0)", (self._root_id(),)
        )

    def _analyze_depth(self, depth: int) -> None:
        "Analyzes the Collider positions under the Scheduler's at `depth`, then their children."
        self._connection.execute(COLLIDER_LAYER, (depth,))
        self._connection.execute(SCHEDULER_LAYER, (depth,))

    def _max_depth(self) -> int:
        depth: int = self._connection.execute(
            "SELECT MAX(depth) FROM atlas.states"
        ).fetchone()[0]
        return depth

    def _require_every_state_analyzed(self) -> None:
        missing = self._connection.execute(
            "SELECT COUNT(*) FROM atlas.states state WHERE NOT EXISTS"
            " (SELECT 1 FROM scheduler_equilibrium"
            " WHERE scheduler_equilibrium.id = state.id)"
        ).fetchone()[0]
        if missing:
            raise RuntimeError(f"{missing:,} states were never reached from the root")

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


def analyze_equilibrium(atlas: Path, analysis: Path) -> None:
    """
    Writes the equilibrium analysis of `atlas` to `analysis`, which must not exist. It
    appears only once it is complete: a failed analysis leaves nothing behind to refuse
    the next one.
    """
    if analysis.exists():
        raise FileExistsError(analysis)
    partial = analysis.with_name(analysis.name + ".partial")
    partial.unlink(missing_ok=True)
    try:
        with EquilibriumAnalysis.open(atlas, partial) as equilibrium_analysis:
            equilibrium_analysis.analyze()
        os.replace(partial, analysis)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            partial.unlink()
        raise


def layer_summaries(atlas: Path, analysis: Path) -> ZVec[LayerSummary]:
    if not analysis.exists():
        raise FileNotFoundError(analysis)
    with EquilibriumAnalysis.open(atlas, analysis) as equilibrium_analysis:
        return equilibrium_analysis.layer_summaries()
