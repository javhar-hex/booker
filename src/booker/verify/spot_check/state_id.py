"""The identity of a position in the atlas that is audited."""

from __future__ import annotations

import dataclasses as dc


@dc.dataclass(frozen=True, slots=True, order=True)
class StateId:
    "A row of the `states` table; not a team index, nor a depth."

    value: int

    def __str__(self) -> str:
        return str(self.value)
