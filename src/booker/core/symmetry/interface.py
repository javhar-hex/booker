"""What is asked of the symmetries of states, answered by more than one library."""

from __future__ import annotations

from typing import Protocol

from javhar_util.immutables import ZSet

from booker.core.model.pairing import Pairing
from booker.core.model.state import State
from booker.core.symmetry.orbits import PairingOrbits


class Symmetry(Protocol):
    """
    Decisions about the symmetries of states. The generator needs canonical forms, which
    only BLISS gives at scale; these are the questions that any graph library can answer,
    so implementations on different libraries can be compared with one another.
    """

    def are_isomorphic(self, first: State, second: State) -> bool:
        "Is there a relabelling of the teams that turns `first` into `second`?"
        ...

    def orbits(self, state: State, pairings: ZSet[Pairing]) -> PairingOrbits:
        """
        `pairings` partitioned into orbits under the automorphisms of `state`. They must
        be closed under those automorphisms, as the legal pairings are.
        """
        ...
