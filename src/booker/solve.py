"""The retrograde minimax solver: backs up the GTVs of the atlas from its last layer."""

from __future__ import annotations

from booker.atlas.atlas import Atlas
from booker.core.model.invariants import MAX_MATCHES


def solve(path: str) -> int:
    """
    Backs up the GTVs of the atlas at `path`, which must be fully generated, and returns
    the GTV of its root.
    """
    with Atlas.open(path) as atlas:
        if unexpanded := atlas.num_unexpanded():
            raise RuntimeError(
                f"Cannot solve truncated atlas: {unexpanded:,} unexpanded states"
            )
        solver = atlas.retrograde_solver()
        solver.reset_gtvs()
        # A state's children are one match deeper, so their GTVs are backed up before its.
        for depth in range(MAX_MATCHES, -1, -1):
            solver.back_up(depth)
            if missing := solver.num_unsolved(depth):
                raise RuntimeError(
                    f"Bellman backup missing {missing} GTVs at depth {depth}"
                )
        solver.mark_solved()
        return solver.root_gtv()
