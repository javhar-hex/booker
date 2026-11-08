"""What is asked of the symmetries of states, answered by more than one library."""

from __future__ import annotations

import dataclasses as dc
from collections import Counter
from typing import Protocol

from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.state import State
from booker.core.symmetry.orbits import PairingOrbits


class Symmetry(Protocol):
    """
    Decisions about the symmetries of states. The generator needs canonical forms, which
    only BLISS gives at scale; these are the questions that any graph library can answer,
    so implementations on different libraries can be compared with one another.

    An implementation names this protocol as a base class: it adds nothing to the class,
    but it says what the class is for, and a method that is missing or has drifted is an
    error where the class is defined, not where it is first used.
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


def signature(state: State) -> ZVec[TeamSignature]:
    """
    A cheap necessary condition for `Symmetry.are_isomorphic`: each team's record and
    number of previous opponents, sorted. States that are isomorphic have equal
    signatures; the converse does not hold, so equal signatures are not an answer, but
    different ones are.
    """
    degree = Counter(
        team for pairing in state.past_pairings for team in (pairing.lhs, pairing.rhs)
    )
    return ZVec(
        sorted(
            TeamSignature(wins=record.wins, losses=record.losses, degree=degree[team])
            for team, record in zip(state.teams, state.records)
        )
    )


@dc.dataclass(frozen=True, slots=True, order=True)
class TeamSignature:
    "What an isomorphism cannot change about one team."

    wins: int
    losses: int
    degree: int
