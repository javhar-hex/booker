"""How positions are canonicalized while the atlas is generated."""

from __future__ import annotations

import enum
from collections.abc import Iterable

from booker.core.model.state import State
from booker.core.symmetry.canonical_schedule import canonical_state
from booker.generate.canonicalizer import Canonicalizer
from booker.generate.state_canonicalizer import StateCanonicalizer


class BlissCanonicalizer(Canonicalizer):
    def __call__(self, state: State) -> State:
        return canonical_state(state)


class Backend(enum.Enum):
    BLISS = "bliss"
    VF2 = "vf2"

    def canonicalizer(self, known: Iterable[State]) -> Canonicalizer:
        "One that stays consistent with `known`, the states already in an atlas."
        if self is Backend.VF2:
            return StateCanonicalizer(known)
        else:
            return BlissCanonicalizer()


BLISS = Backend.BLISS
VF2 = Backend.VF2
