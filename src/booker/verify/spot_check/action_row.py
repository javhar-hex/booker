"""A row of the `actions` table."""

from __future__ import annotations

import dataclasses as dc
from typing import ClassVar

from javhar_util.immutables import ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.team import Team
from booker.core.symmetry.orbits import PairingOrbits
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId


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

    @classmethod
    def require_orbits(
        cls, state_id: StateId, action_rows: ZVec[ActionRow], orbits: PairingOrbits
    ) -> None:
        """
        Raises `AuditFailure` unless each of `orbits` has exactly one of the stored
        `action_rows` for a pairing, which carries the orbit's size.
        """
        sizes = {action_row.pairing: action_row.class_size for action_row in action_rows}
        for orbit in orbits:
            representatives = [pairing for pairing in sizes if pairing in orbit.members]
            if len(representatives) != 1:
                raise AuditFailure.of(
                    state_id,
                    f"orbit representatives: {len(representatives)} stored for the "
                    f"orbit of {min(orbit.members)} ({orbit.size} pairings): "
                    f"{representatives}",
                )
            if sizes[representatives[0]] != orbit.size:
                raise AuditFailure.of(
                    state_id,
                    f"orbit sizes: {representatives[0]} is stored "
                    f"as {sizes[representatives[0]]}, but its orbit has {orbit.size}",
                )
