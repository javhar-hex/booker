"""Pairings that symmetries of a state map onto one another; nothing here finds them."""

from __future__ import annotations

import dataclasses as dc
from collections.abc import Iterator

from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.symmetry.relabelling import Relabelling


@dc.dataclass(frozen=True, slots=True)
class PairingOrbit:
    """
    Pairings that the symmetries of a schedule map onto one another, so that adding any
    one of them gives isomorphic schedules.
    """

    members: ZSet[Pairing]

    def __post_init__(self) -> None:
        if not self.members:
            raise ValueError("an orbit has at least one pairing")

    @classmethod
    def of(cls, pairing: Pairing, symmetries: ZVec[Relabelling]) -> PairingOrbit:
        "Every image of `pairing` under the group that `symmetries` generate."
        members = {pairing}
        frontier = [pairing]
        while frontier:
            current = frontier.pop()
            for image in (symmetry.pairing(current) for symmetry in symmetries):
                if image not in members:
                    members.add(image)
                    frontier.append(image)
        return cls(members=ZSet(members))

    @property
    def representative(self) -> Pairing:
        return min(self.members)

    @property
    def size(self) -> int:
        return len(self.members)


@dc.dataclass(frozen=True, slots=True)
class PairingOrbits:
    """
    Pairings partitioned into orbits under the symmetries of a state or schedule, in order
    of representative.
    """

    orbits: ZVec[PairingOrbit]

    def __post_init__(self) -> None:
        if sum(orbit.size for orbit in self.orbits) != len(self.pairings):
            raise ValueError("orbits of one schedule cannot overlap")
        representatives = [orbit.representative for orbit in self.orbits]
        if representatives != sorted(representatives):
            raise ValueError("orbits must be in order of representative")

    def __iter__(self) -> Iterator[PairingOrbit]:
        return iter(self.orbits)

    def __len__(self) -> int:
        return len(self.orbits)

    @property
    def pairings(self) -> ZSet[Pairing]:
        return ZSet(pairing for orbit in self.orbits for pairing in orbit.members)
