"""A canonicalizer of states that does not use BLISS, for cross-checking it."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from javhar_util.immutables import ZVec

from booker.core.model.state import State
from booker.core.symmetry.symmetry import TeamSignature, signature
from booker.core.symmetry.vf2_symmetry import Vf2Symmetry
from booker.generate.canonicalizer import Canonicalizer

Signature = ZVec[TeamSignature]


class StateCanonicalizer(Canonicalizer):
    """
    Maps a state to a representative of its isomorphism class: isomorphic states get the
    same one. Which state represents a class depends on what the canonicalizer has been
    shown, starting with `known`, so a generation that resumes must hand it the states
    that are already stored. That memory is deliberate, and it is mutable: each state
    that is the first of its class is remembered as it is met. The cost of a state grows
    with the number of classes already met, so it suits a prefix of the atlas better than
    all of it.
    """

    def __init__(self, known: Iterable[State]) -> None:
        self._symmetry = Vf2Symmetry()
        self._representatives: defaultdict[Signature, list[State]] = defaultdict(list)
        for state in known:
            self._representatives[signature(state)].append(state)

    def __call__(self, state: State) -> State:
        candidates = self._representatives[signature(state)]
        for representative in candidates:
            if self._symmetry.are_isomorphic(state, representative):
                return representative
        candidates.append(state)
        return state
