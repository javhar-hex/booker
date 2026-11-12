"""Pairings, counted as orbits and in all."""

from __future__ import annotations

import dataclasses as dc

from javhar_util.immutables import ZVec

from booker.verify.spot_check.action_row import ActionRow


@dc.dataclass(frozen=True, slots=True)
class PairingCount:
    """
    Pairings counted two ways: `orbits`, as the groups of pairings that the symmetries of a
    position map onto one another, and `pairings`, as every labelled pairing in them.
    """

    orbits: int
    pairings: int

    @classmethod
    def none(cls) -> PairingCount:
        return cls(orbits=0, pairings=0)

    @classmethod
    def of(cls, rows: ZVec[ActionRow]) -> PairingCount:
        "The pairings of a position, whose stored actions are its orbits."
        return cls(orbits=len(rows), pairings=sum(row.class_size for row in rows))

    def plus(self, other: PairingCount) -> PairingCount:
        return PairingCount(
            orbits=self.orbits + other.orbits, pairings=self.pairings + other.pairings
        )
