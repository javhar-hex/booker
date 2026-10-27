from __future__ import annotations

import dataclasses as dc

from booker.core.model.schedule import Schedule
from booker.core.symmetry.coloured_graph import ColouredGraph


@dc.dataclass(frozen=True, slots=True)
class CanonicalSchedule:
    """
    The representative of a schedule's isomorphism class: two schedules have equal
    canonical schedules exactly when one is a relabelling of the other.
    """

    schedule: Schedule

    @classmethod
    def of(cls, schedule: Schedule) -> CanonicalSchedule:
        relabelling = ColouredGraph(schedule=schedule).canonical_relabelling
        return cls(schedule=relabelling.schedule(schedule))
