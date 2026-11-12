"""What the atlas expander asks of the way states are canonicalized."""

from __future__ import annotations

from collections.abc import Iterable

from booker.core.model.state import State
from booker.core.symmetry.state_symmetries import BLISS
from booker.core.symmetry.state_symmetry import StateSymmetry
from booker.expand.bliss_canonicalizer import BlissCanonicalizer
from booker.expand.memo_canonicalizer import MemoCanonicalizer


class StateCanonicalizer:
    """
    Maps a state to the representative of its isomorphism class, as `symmetry` allows.
    Only BLISS gives canonical forms; for any other symmetry the representative is the
    first state of its class that has been shown, starting with `known_states`, the states
    already in an atlas. That memory is mutable, and it is the one thing here that is.
    """

    def __init__(self, symmetry: StateSymmetry, known_states: Iterable[State]) -> None:
        self._canonicalizer: BlissCanonicalizer | MemoCanonicalizer = (
            BlissCanonicalizer()
            if symmetry == BLISS
            else MemoCanonicalizer(symmetry=symmetry, known_states=known_states)
        )

    def __call__(self, state: State) -> State:
        return self._canonicalizer(state)
