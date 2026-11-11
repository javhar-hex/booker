"""A state canonicalizer for a symmetry that has no canonical forms of its own."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from javhar_util.immutables import ZVec

from booker.core.model.state import State
from booker.core.symmetry.state_symmetry import StateSymmetry, TeamSignature, signature
from booker.generate.state_canonicalizer import StateCanonicalizer

Signature = ZVec[TeamSignature]


class MemoCanonicalizer(StateCanonicalizer):
    """
    Maps a state to a representative of its isomorphism class, for any `StateSymmetry`:
    isomorphic states get the same one. The representative of a class is the first state
    of it that the canonicalizer has been shown, starting with `known`, so a generation
    that resumes must hand it the states that are already stored. That memory is
    deliberate, and it is mutable: each state that is the first of its class is
    remembered as it is met. The cost of a state grows with the number of classes already
    met, so it suits a prefix of the atlas better than all of it.
    """

    def __init__(self, symmetry: StateSymmetry, known: Iterable[State]) -> None:
        self._symmetry = symmetry
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
