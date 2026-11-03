"""What the atlas hands out: identified positions and per-depth summaries."""

from __future__ import annotations

import dataclasses as dc

from booker.core.model.state import State


@dc.dataclass(frozen=True, slots=True, order=True)
class StateId:
    "A stored position; not interchangeable with a team index or a depth."

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValueError(f"stored positions are numbered from 1, got {self.value}")


@dc.dataclass(frozen=True, slots=True)
class StoredState:
    id: StateId
    state: State


@dc.dataclass(frozen=True, slots=True)
class DepthSummary:
    "One number of matches played; the values are the positions', once solved."

    depth: int
    num_states: int
    num_colliders: int
    num_pairings: int
    min_value: int | None
    max_value: int | None
