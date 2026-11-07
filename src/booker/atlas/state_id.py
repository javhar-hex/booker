"""The identity of a position that an atlas stores."""

from __future__ import annotations

import dataclasses as dc


@dc.dataclass(frozen=True, slots=True, order=True)
class StateId:
    "A stored position; not interchangeable with a team index or a depth."

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValueError(f"stored positions are numbered from 1, got {self.value}")
