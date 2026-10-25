from __future__ import annotations

import dataclasses as dc


@dc.dataclass(frozen=True, slots=True, order=True)
class Team:
    """
    Semantic object representing a live team. The `index` identifies the team within one
    `State`; it is not identified across states.
    """

    index: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(f"team index must be >= 0, got {self.index}")
