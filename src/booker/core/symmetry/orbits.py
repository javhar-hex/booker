from __future__ import annotations

import dataclasses as dc
from collections.abc import Iterator

from booker.core.model.pairing import Pairing
from booker.core.model.schedule import Schedule
from booker.core.symmetry.coloured_graph import ColouredGraph
from booker.core.symmetry.relabelling import Relabelling
from util.dtypes.immutables.z_set import ZSet
from util.dtypes.immutables.z_vec import ZVec


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
    The pairings that may be added to a schedule, partitioned into orbits under the
    schedule's symmetries, in order of representative.
    """

    orbits: ZVec[PairingOrbit]

    def __post_init__(self) -> None:
        if sum(orbit.size for orbit in self.orbits) != len(self.pairings):
            raise ValueError("orbits of one schedule cannot overlap")
        representatives = [orbit.representative for orbit in self.orbits]
        if representatives != sorted(representatives):
            raise ValueError("orbits must be in order of representative")

    @classmethod
    def of(cls, schedule: Schedule, additions: ZSet[Pairing]) -> PairingOrbits:
        """
        Which pairings may be added is for the rules of each game to say; being legal,
        they are closed under the schedule's symmetries, and none is booked already.
        """
        if booked := additions & schedule.pairings:
            raise ValueError(f"already booked: {sorted(booked)}")
        symmetries = ColouredGraph(schedule=schedule).automorphism_generators
        remaining = set(additions)
        orbits = []
        while remaining:
            orbit = PairingOrbit.of(min(remaining), symmetries)
            if strays := orbit.members - additions:
                raise ValueError(
                    f"additions not closed under symmetry: {sorted(strays)}"
                )
            remaining -= set(orbit.members)
            orbits.append(orbit)
        return cls(orbits=ZVec(orbits))

    def __iter__(self) -> Iterator[PairingOrbit]:
        return iter(self.orbits)

    def __len__(self) -> int:
        return len(self.orbits)

    @property
    def pairings(self) -> ZSet[Pairing]:
        return ZSet(pairing for orbit in self.orbits for pairing in orbit.members)
