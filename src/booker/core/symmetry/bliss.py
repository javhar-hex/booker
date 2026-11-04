"""The symmetries of states by BLISS, as the generator finds them."""

from __future__ import annotations

from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.symmetry.bliss_graph import BlissGraph
from booker.core.symmetry.canonical import canonical_state
from booker.core.symmetry.orbits import PairingOrbit, PairingOrbits


class BlissSymmetry:
    "Canonical forms and the generators of the automorphism group, from BLISS."

    def are_isomorphic(self, first: State, second: State) -> bool:
        return canonical_state(first) == canonical_state(second)

    def orbits(self, state: State, pairings: ZSet[Pairing]) -> PairingOrbits:
        return orbits_of_schedule(Schedule.empty(state), pairings)


def orbits_of_schedule(schedule: Schedule, additions: ZSet[Pairing]) -> PairingOrbits:
    """
    The pairings that may be added to a schedule, partitioned into orbits under its
    symmetries. Which may be added is for the rules of each game to say; being legal,
    they are closed under the schedule's symmetries, and none is booked already.
    """
    if booked := additions & schedule.pairings:
        raise ValueError(f"already booked: {sorted(booked)}")
    symmetries = BlissGraph(schedule=schedule).automorphism_generators
    remaining = set(additions)
    orbits = []
    while remaining:
        orbit = PairingOrbit.of(min(remaining), symmetries)
        if strays := orbit.members - additions:
            raise ValueError(f"additions not closed under symmetry: {sorted(strays)}")
        remaining -= set(orbit.members)
        orbits.append(orbit)
    return PairingOrbits(orbits=ZVec(orbits))
