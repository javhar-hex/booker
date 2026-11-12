"""A row of the `actions` table."""

from __future__ import annotations

import dataclasses as dc
from typing import ClassVar

from booker.core.model.pairing import Pairing
from booker.core.model.team import Team
from booker.verify.state_id import StateId


@dc.dataclass(frozen=True, slots=True)
class ActionRow:
    "The Scheduler's pairing from a position, and where each winner leads."

    COLUMNS: ClassVar[str] = "lhs,rhs,repeat_cost,lhs_wins,rhs_wins,class_size,value"
    "The columns of the row that `of` takes, in order."

    pairing: Pairing
    repeat_cost: int
    lhs_wins: StateId
    rhs_wins: StateId
    class_size: int
    value: int | None

    @classmethod
    def of(cls, row: tuple[int, int, int, int, int, int, int | None]) -> ActionRow:
        index_lhs, index_rhs, repeat_cost, lhs_wins, rhs_wins, class_size, value = row
        return cls(
            pairing=Pairing.of(Team(index=index_lhs), Team(index=index_rhs)),
            repeat_cost=repeat_cost,
            lhs_wins=StateId(value=lhs_wins),
            rhs_wins=StateId(value=rhs_wins),
            class_size=class_size,
            value=value,
        )
