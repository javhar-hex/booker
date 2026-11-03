"""The retrograde minimax solver: values the atlas from its last layer back."""

from __future__ import annotations

from booker.atlas.storage import Atlas
from booker.core.model.invariants import MAX_MATCHES


def solve(path: str) -> None:
    "Backs up the values of the atlas at `path`, which must be fully generated."
    with Atlas.open(path) as atlas:
        if unexpanded := atlas.num_unexpanded():
            raise RuntimeError(
                f"Cannot solve truncated atlas: {unexpanded:,} unexpanded states"
            )
        atlas.reset_values()
        # A state's children are one match deeper, so they are valued before it.
        for depth in range(MAX_MATCHES, -1, -1):
            atlas.back_up(depth)
            if missing := atlas.num_unvalued(depth):
                raise RuntimeError(
                    f"Bellman backup missing {missing} values at depth {depth}"
                )
        atlas.mark_solved()
        print(f"root minimax value: {atlas.root_value()}")
