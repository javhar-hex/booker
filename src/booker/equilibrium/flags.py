"""
Equilibrium pass over a solved atlas, written to a separate database.

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

from booker.equilibrium.database import FlagsDatabase
from booker.equilibrium.layers import LayerSummary


def build(atlas: Path, flags: Path) -> None:
    """
    Writes the flags of `atlas` to `flags`, which must not exist. It appears only once it
    is complete: a failed build leaves nothing behind to refuse the next one.
    """
    if flags.exists():
        raise FileExistsError(flags)
    partial = flags.with_name(flags.name + ".partial")
    partial.unlink(missing_ok=True)
    try:
        _build_into(atlas, partial)
        os.replace(partial, flags)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            partial.unlink()
        raise


def summary(atlas: Path, flags: Path) -> ZVec[LayerSummary]:
    if not flags.exists():
        raise FileNotFoundError(flags)
    with FlagsDatabase.open(atlas, flags) as database:
        return database.layers()


def _build_into(atlas: Path, flags: Path) -> None:
    with FlagsDatabase.open(atlas, flags) as database:
        database.require_solved()
        database.create_flag_tables()
        with database.transaction():
            database.flag_root()
            for depth in range(database.max_depth()):
                database.flag_depth(depth)
        database.require_every_state_flagged()
