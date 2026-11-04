"""What the generator asks of the way states are canonicalized."""

from __future__ import annotations

from typing import Protocol

from booker.core.model.state import State


class Canonicalizer(Protocol):
    """
    Maps a state to the representative of its isomorphism class. An implementation names
    this protocol as a base class, so that a method that is missing or has drifted is an
    error where the class is defined.
    """

    def __call__(self, state: State) -> State: ...
