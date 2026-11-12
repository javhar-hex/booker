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
from pathlib import Path

from javhar_util.immutables import ZVec

from booker.equilibrium.equilibrium_database import EquilibriumDatabase
from booker.equilibrium.layer_summary import LayerSummary


def analyze_equilibrium(atlas: Path, analysis: Path) -> None:
    """
    Writes the equilibrium analysis of `atlas` to `analysis`, which must not exist. It appears only once it
    is complete: a failed analysis leaves nothing behind to refuse the next one.
    """
    if analysis.exists():
        raise FileExistsError(analysis)
    partial = analysis.with_name(analysis.name + ".partial")
    partial.unlink(missing_ok=True)
    try:
        _analyze_into(atlas, partial)
        os.replace(partial, analysis)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            partial.unlink()
        raise


def layer_summaries(atlas: Path, analysis: Path) -> ZVec[LayerSummary]:
    if not analysis.exists():
        raise FileNotFoundError(analysis)
    with EquilibriumDatabase.open(atlas, analysis) as database:
        return database.layer_summaries()


def _analyze_into(atlas: Path, analysis: Path) -> None:
    with EquilibriumDatabase.open(atlas, analysis) as database:
        database.require_solved()
        database.create_tables()
        with database.transaction():
            database.analyze_root()
            for depth in range(database.max_depth()):
                database.analyze_depth(depth)
        database.require_every_state_analyzed()
