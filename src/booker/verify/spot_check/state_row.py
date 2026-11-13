"""A row of the `states` table, with its position decoded."""

from __future__ import annotations

import dataclasses as dc
from typing import ClassVar

from booker.atlas.packed_state import PackedState
from booker.core.model.invariants import CHAMPION_WINS, MAX_MATCHES
from booker.core.model.state import State
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId


@dc.dataclass(frozen=True, slots=True)
class StateRow:
    "What the atlas stores of one position."

    COLUMNS: ClassVar[str] = "key,depth,active,gtv,expanded"
    "The columns of the row that `of` takes, in order."

    state: State
    depth: int
    num_teams: int
    gtv: int | None
    is_expanded: bool

    @classmethod
    def of(
        cls, state_id: StateId, row: tuple[bytes, int, int, int | None, int]
    ) -> StateRow:
        key, depth, num_teams, gtv, expanded = row
        try:
            state = PackedState(data=key).state
        except ValueError as error:
            raise AuditFailure.of(state_id, f"invalid position: {error}") from error
        return cls(
            state=state,
            depth=depth,
            num_teams=num_teams,
            gtv=gtv,
            is_expanded=bool(expanded),
        )

    def require_consistent(self, state_id: StateId) -> None:
        "Raises `AuditFailure` if the row disagrees with its own position."
        state = self.state
        if self.num_teams != state.size or not 0 <= self.depth <= MAX_MATCHES:
            raise AuditFailure.of(state_id, "inconsistent team count or depth")
        if self.depth != state.matches_played:
            raise AuditFailure.of(
                state_id,
                f"depth {self.depth}, but its teams have "
                f"played {state.matches_played} matches",
            )
        if state.is_decided:
            if state.records[0].wins != CHAMPION_WINS or not self.is_expanded:
                raise AuditFailure.of(state_id, "a bad decided state")
        elif any(record.wins >= CHAMPION_WINS for record in state.records):
            raise AuditFailure.of(state_id, "a champion, with teams still playing")
