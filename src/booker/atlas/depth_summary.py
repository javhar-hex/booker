"""What an atlas holds at one depth."""

from __future__ import annotations

import dataclasses as dc


@dc.dataclass(frozen=True, slots=True)
class DepthSummary:
    """
    The positions at one depth, which is a number of matches played: how many there are,
    how many Collider positions and labelled pairings they lead to, and the least and
    greatest value among the positions, which are `None` until the atlas is solved.
    """

    depth: int
    num_states: int
    num_colliders: int
    num_pairings: int
    min_value: int | None
    max_value: int | None
