"""The symmetries of states by BLISS, as the generator finds them."""

from __future__ import annotations

from javhar_util.immutables import ZSet

from booker.core.model.pairing import Pairing
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.symmetry.canonical import CanonicalSchedule
from booker.core.symmetry.orbits import PairingOrbits


class BlissSymmetry:
    def are_isomorphic(self, first: State, second: State) -> bool:
        return self._canonical(first) == self._canonical(second)

    def orbits(self, state: State, pairings: ZSet[Pairing]) -> PairingOrbits:
        return PairingOrbits.of(Schedule.empty(state), pairings)

    def _canonical(self, state: State) -> CanonicalSchedule:
        return CanonicalSchedule.of(Schedule.empty(state))
