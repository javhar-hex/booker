"""A state canonicalizer for a symmetry that has no canonical forms of its own."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from booker.core.model.state import State
from booker.core.symmetry.state_signature import StateSignature
from booker.core.symmetry.state_symmetry import StateSymmetry


class MemoCanonicalizer:
    """
    Maps a state to a representative of its isomorphism class, for any `StateSymmetry`:
    isomorphic states get the same one. The representative of a class is the first state
    of it that the canonicalizer has been shown, starting with `known_states`, so a generation
    that resumes must hand it the states that are already stored. That memory is
    deliberate, and it is mutable: each state that is the first of its class is
    remembered as it is met. The cost of a state grows with the number of classes already
    met, so it suits a prefix of the atlas better than all of it.
    """

    def __init__(self, symmetry: StateSymmetry, known_states: Iterable[State]) -> None:
        self._symmetry = symmetry
        self._representatives: defaultdict[StateSignature, list[State]] = defaultdict(
            list
        )
        for state in known_states:
            self._representatives[StateSignature.of(state)].append(state)

    def __call__(self, state: State) -> State:
        candidates = self._representatives[StateSignature.of(state)]
        for representative in candidates:
            if self._symmetry.are_isomorphic(state, representative):
                return representative
        candidates.append(state)
        return state
