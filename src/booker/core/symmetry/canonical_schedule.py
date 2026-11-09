"""The representative of an isomorphism class of schedules or states, by BLISS."""

from __future__ import annotations

import dataclasses as dc

from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.symmetry.bliss_graph import BlissGraph


def canonical_state(state: State) -> State:
    "The state that every state isomorphic to `state` is relabelled to."
    return CanonicalSchedule.of(Schedule.empty(state)).schedule.state


@dc.dataclass(frozen=True, slots=True)
class CanonicalSchedule:
    """
    The representative of a schedule's isomorphism class: two schedules have equal
    canonical schedules exactly when one is a relabelling of the other.
    """

    schedule: Schedule

    @classmethod
    def of(cls, schedule: Schedule) -> CanonicalSchedule:
        relabelling = BlissGraph(schedule=schedule).canonical_relabelling
        return cls(schedule=relabelling.schedule(schedule))
