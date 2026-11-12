"""What the checks of one position counted."""

from __future__ import annotations

import dataclasses as dc

from javhar_util.immutables import ZVec

from booker.verify.action_row import ActionRow


@dc.dataclass(frozen=True, slots=True)
class Tally:
    actions: int
    pairings: int

    @classmethod
    def of(cls, rows: ZVec[ActionRow]) -> Tally:
        "The actions of a position, and the labelled pairings that they stand for."
        return cls(actions=len(rows), pairings=sum(row.class_size for row in rows))
