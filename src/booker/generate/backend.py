"""How positions are canonicalized while the atlas is generated."""

from __future__ import annotations

import enum
from collections.abc import Iterable
from typing import Protocol

from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.symmetry.canonical import CanonicalSchedule
from booker.generate.vf2 import MAX_DEPTH as VF2_MAX_DEPTH
from booker.generate.vf2 import VF2PrefixCanonicalizer


class Canonicalizer(Protocol):
    "Maps a state to the representative of its isomorphism class."

    def __call__(self, state: State) -> State: ...


class BlissCanonicalizer:
    def __call__(self, state: State) -> State:
        return CanonicalSchedule.of(Schedule.empty(state)).schedule.state


class Backend(enum.Enum):
    BLISS = "bliss"
    VF2 = "vf2"

    @property
    def max_depth(self) -> int:
        "The deepest layer, in matches played, that this backend can generate."
        if self is Backend.VF2:
            return VF2_MAX_DEPTH
        else:
            return MAX_MATCHES

    def canonicalizer(self, known: Iterable[State]) -> Canonicalizer:
        "One that stays consistent with `known`, the states already in an atlas."
        if self is Backend.VF2:
            return VF2PrefixCanonicalizer(known)
        else:
            return BlissCanonicalizer()


BLISS = Backend.BLISS
VF2 = Backend.VF2
