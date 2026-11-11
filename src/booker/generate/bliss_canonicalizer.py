"""The canonical state by BLISS, which generation uses unless it cross-checks."""

from __future__ import annotations

import dataclasses as dc

from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.symmetry.bliss_graph import BlissGraph
from booker.generate.state_canonicalizer import StateCanonicalizer


@dc.dataclass(frozen=True, slots=True)
class BlissCanonicalizer(StateCanonicalizer):
    "The state that every state isomorphic to the given one is relabelled to."

    def __call__(self, state: State) -> State:
        relabelling = BlissGraph(schedule=Schedule.empty(state)).canonical_relabelling
        return relabelling.state(state)
