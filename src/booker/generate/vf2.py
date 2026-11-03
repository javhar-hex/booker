"""
A slow graph-matching canonicalizer for a small executable sample, independent of
BLISS. Representatives are the first-discovered labelled states, so never use it on the
full atlas.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from javhar_util.immutables import ZVec

from booker.core.model.state import State
from booker.core.symmetry.invariant import TeamSignature, signature
from booker.core.symmetry.vf2 import Vf2Symmetry

Signature = ZVec[TeamSignature]

MAX_DEPTH = 6
"The deepest layer, counted in matches played, that is still small enough to use."


class VF2PrefixCanonicalizer:
    """
    Maps a state to the first state seen that is isomorphic to it, or to itself if it is
    the first of its kind. Remembering what it has seen is the point, not a shortcut:
    the representatives are whichever labelled states happened to come first.
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
