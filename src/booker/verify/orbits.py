"""Whether the stored pairings are exactly one per orbit of the legal pairings."""

from __future__ import annotations

from javhar_util.immutables import ZMap

from booker.core.model.pairing import Pairing
from booker.core.model.state import State
from booker.game.rules import legal_pairings
from booker.verify.failure import AuditFailure
from booker.verify.isomorphism import ColouredGraph, Mode, are_isomorphic


def check_orbits(state: State, stored: ZMap[Pairing, int], mode: Mode) -> None:
    """
    Each legal pairing is equivalent, under the state's automorphisms, to exactly one
    stored pairing, whose class size is the number of legal pairings equivalent to it.
    """
    hits = dict.fromkeys(stored, 0)
    for pairing in legal_pairings(state):
        matches = [
            representative
            for representative in stored
            if are_equivalent(state, pairing, representative, mode)
        ]
        if len(matches) != 1:
            raise AuditFailure(
                f"orbit representatives: {pairing} is equivalent to {matches} in {state}"
            )
        hits[matches[0]] += 1
    if ZMap(hits) != stored:
        raise AuditFailure(f"orbit sizes: found {hits}, stored {dict(stored.items())}")


def are_equivalent(state: State, x: Pairing, y: Pairing, mode: Mode) -> bool:
    "Is there an automorphism of the state that maps pairing `x` onto pairing `y`?"
    if state.has_met(x) != state.has_met(y):
        return False
    return are_isomorphic(
        ColouredGraph.marked(state, x), ColouredGraph.marked(state, y), mode
    )
