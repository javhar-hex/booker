"""
The symmetries of states by VF2 (VF2++, in networkx), a different algorithm from the
generator's BLISS. Orbits are found by asking, of each pairing in turn, whether it is
equivalent to the first of an orbit already found, where the generator takes the
generators of the automorphism group from BLISS and closes the pairings under them.

igraph's own VF2 is not used: on states with many interchangeable teams and no result to
find, it backtracks for seconds where this takes milliseconds.
"""

from __future__ import annotations

import dataclasses as dc

import networkx as nx
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.symmetry.orbits import PairingOrbit, PairingOrbits
from booker.core.symmetry.symmetry import Symmetry, signature


@dc.dataclass(frozen=True, slots=True)
class _Label:
    "What a team is called in a graph: its record, and whether it is one of a pair."

    record: Record
    is_paired: bool


@dc.dataclass(frozen=True, slots=True)
class _LabelledGraph:
    labels: ZVec[_Label]
    edges: ZSet[Pairing]

    @classmethod
    def of(cls, state: State) -> _LabelledGraph:
        "Teams labelled by record, adjacent when they have met."
        return cls(
            labels=ZVec(_Label(record, is_paired=False) for record in state.records),
            edges=state.met,
        )

    @classmethod
    def marked(cls, state: State, pairing: Pairing) -> _LabelledGraph:
        "The state's graph, with the two teams of `pairing` set apart."
        return cls(
            labels=ZVec(
                _Label(state.record(team), is_paired=pairing.involves(team))
                for team in state.teams
            ),
            edges=state.met,
        )


class Vf2Symmetry(Symmetry):
    "Isomorphism by VF2++, and orbits by comparing pairings with one another."

    def are_isomorphic(self, first: State, second: State) -> bool:
        if signature(first) != signature(second):
            return False
        return _alike(_LabelledGraph.of(first), _LabelledGraph.of(second))

    def orbits(self, state: State, pairings: ZSet[Pairing]) -> PairingOrbits:
        groups: list[list[Pairing]] = []
        for pairing in sorted(pairings):
            for group in groups:
                if self._equivalent(state, group[0], pairing):
                    group.append(pairing)
                    break
            else:
                groups.append([pairing])
        return PairingOrbits(
            orbits=ZVec(PairingOrbit(members=ZSet(group)) for group in groups)
        )

    def _equivalent(self, state: State, x: Pairing, y: Pairing) -> bool:
        if state.has_met(x) != state.has_met(y):
            return False
        return _alike(_LabelledGraph.marked(state, x), _LabelledGraph.marked(state, y))


def _alike(first: _LabelledGraph, second: _LabelledGraph) -> bool:
    graphs: list[nx.Graph[int]] = []
    for g in (first, second):
        graph: nx.Graph[int] = nx.Graph()
        graph.add_nodes_from((i, {"label": label}) for i, label in enumerate(g.labels))
        graph.add_edges_from((e.lhs.index, e.rhs.index) for e in g.edges)
        graphs.append(graph)
    return bool(nx.vf2pp_is_isomorphic(graphs[0], graphs[1], node_label="label"))
