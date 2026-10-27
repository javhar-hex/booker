from __future__ import annotations

import dataclasses as dc
from functools import cached_property

import igraph as ig

from booker.core.model.invariants import CHAMPION_WINS, ELIMINATION_LOSSES
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.schedule import Schedule
from booker.core.symmetry.relabelling import Relabelling
from util.dtypes.immutables.z_vec import ZVec

BLISS_PROVIDER = f"igraph {ig.__version__}"
SCHEDULED_COLOUR = (CHAMPION_WINS + 1) * ELIMINATION_LOSSES


def team_colour(record: Record) -> int:
    "Distinct for every live record, and below `SCHEDULED_COLOUR`."
    return record.wins * ELIMINATION_LOSSES + record.losses


@dc.dataclass(frozen=True)
class ColouredGraph:
    """
    A schedule as the vertex-coloured graph handed to BLISS. Teams are vertices
    coloured by record, adjacent when they have met. Each scheduled pairing is one more
    vertex, in a colour no team has, adjacent to its two teams: colouring the paired
    teams alone would lose who is paired with whom.
    """

    schedule: Schedule

    @cached_property
    def canonical_relabelling(self) -> Relabelling:
        "Isomorphic schedules are relabelled to the same schedule."
        # igraph lists, slot by canonical slot, the original vertex in it (new -> old).
        canonical_order = self._graph.canonical_permutation(color=self._colours)
        size = self.schedule.state.size
        teams_in_order = [vertex for vertex in canonical_order if vertex < size]
        rank = {team: new for new, team in enumerate(teams_in_order)}
        return Relabelling.of([rank[team] for team in range(size)])

    @cached_property
    def automorphism_generators(self) -> ZVec[Relabelling]:
        "Generators of the group of relabellings that leave the schedule unchanged."
        teams = range(self.schedule.state.size)
        generators = self._graph.automorphism_group(color=self._colours)
        return ZVec(Relabelling.of([g[team] for team in teams]) for g in generators)

    @property
    def _scheduled(self) -> list[Pairing]:
        return sorted(self.schedule.pairings)

    @property
    def _colours(self) -> list[int]:
        teams = [team_colour(record) for record in self.schedule.state.records]
        return teams + [SCHEDULED_COLOUR] * len(self._scheduled)

    @property
    def _graph(self) -> ig.Graph:
        state = self.schedule.state
        met = [(p.low.index, p.high.index) for p in state.met]
        gadgets = [
            (state.size + k, team.index)
            for k, pairing in enumerate(self._scheduled)
            for team in (pairing.low, pairing.high)
        ]
        return ig.Graph(n=len(self._colours), edges=met + gadgets, directed=False)
