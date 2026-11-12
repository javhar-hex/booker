"""What an audit found."""

from __future__ import annotations

import dataclasses as dc

from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.verify.id_range import IdRange


@dc.dataclass(frozen=True, slots=True)
class AuditReport:
    ids: IdRange
    strict: StateSymmetry | None
    states: int
    actions: int
    pairings: int
    is_solved: bool
    unexpanded: int

    def __str__(self) -> str:
        how = (
            "children and orbits not compared"
            if self.strict is None
            else f"children and orbits compared by {self.strict.name}"
        )
        return (
            f"PASS: ids {self.ids}: checked {self.states:,} states / {self.actions:,} "
            f"actions ({self.pairings:,} labelled pairings), {how}, "
            f"solved={self.is_solved}, unexpanded={self.unexpanded:,}"
        )
