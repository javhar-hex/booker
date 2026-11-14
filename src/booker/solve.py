"""The retrograde minimax solver: backs up the GTVs of the atlas from its last layer."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from booker.atlas.atlas import Atlas
from booker.core.model.invariants import MAX_MATCHES


def solve_atlas(path: Path, log: Callable[[str], None]) -> None:
    """
    Backs up the GTVs of the atlas at `path`, which must be fully expanded, and marks it
    solved; `log` hears of each layer and, at the end, of the GTV of the root.
    """
    with Atlas.open(path) as atlas:
        num_unexpanded_states = atlas.num_unexpanded()
        if num_unexpanded_states:
            raise RuntimeError(
                f"Cannot solve truncated atlas: {num_unexpanded_states:,} unexpanded states"
            )
        solver = atlas.retrograde_solver()
        solver.reset_gtvs()
        # A state's children are one match deeper, so their GTVs are backed up before its.
        for depth in range(MAX_MATCHES, -1, -1):
            log(f"backing up depth {depth:02d}")
            solver.back_up(depth)
            num_unsolved = solver.num_unsolved(depth)
            if num_unsolved:
                raise RuntimeError(
                    f"{num_unsolved:,} positions at depth {depth} have no GTV after the backup"
                )
        solver.mark_solved()
        log(f"root GTV: {solver.root_gtv()}")
