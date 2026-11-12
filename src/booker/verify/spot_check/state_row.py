"""A row of the `states` table, with its position decoded."""

from __future__ import annotations

import dataclasses as dc
from typing import ClassVar

from booker.atlas.packed_state import PackedState
from booker.core.model.state import State
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId


@dc.dataclass(frozen=True, slots=True)
class StateRow:
    "What the atlas stores of one position."

    COLUMNS: ClassVar[str] = "key,depth,active,value,expanded"
    "The columns of the row that `of` takes, in order."

    state: State
    depth: int
    num_teams: int
    value: int | None
    is_expanded: bool

    @classmethod
    def of(
        cls, state_id: StateId, row: tuple[bytes, int, int, int | None, int]
    ) -> StateRow:
        key, depth, num_teams, value, expanded = row
        try:
            state = PackedState(data=key).state
        except ValueError as error:
            raise AuditFailure.of(state_id, f"invalid position: {error}") from error
        return cls(
            state=state,
            depth=depth,
            num_teams=num_teams,
            value=value,
            is_expanded=bool(expanded),
        )
