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
from booker.core.model.state import State
from booker.core.symmetry.invariant import signature, team_colour
from booker.core.symmetry.orbits import PairingOrbit, PairingOrbits


@dc.dataclass(frozen=True, slots=True)
class _ColouredGraph:
    colours: ZVec[int]
    edges: ZSet[Pairing]

    @classmethod
    def of(cls, state: State) -> _ColouredGraph:
        "Teams coloured by record, adjacent when they have met."
        return cls(
            colours=ZVec(team_colour(record) for record in state.records),
            edges=state.met,
        )

    @classmethod
    def marked(cls, state: State, pairing: Pairing) -> _ColouredGraph:
        "The state's graph, with the two teams of `pairing` set apart by colour."
        return cls(
            colours=ZVec(
                2 * team_colour(state.record(team)) + pairing.involves(team)
                for team in state.teams
            ),
            edges=state.met,
        )


class Vf2Symmetry:
    "Isomorphism by VF2++, and orbits by comparing pairings with one another."

    def are_isomorphic(self, first: State, second: State) -> bool:
        if signature(first) != signature(second):
            return False
        return _alike(_ColouredGraph.of(first), _ColouredGraph.of(second))

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
        return _alike(_ColouredGraph.marked(state, x), _ColouredGraph.marked(state, y))


def _alike(first: _ColouredGraph, second: _ColouredGraph) -> bool:
    graphs: list[nx.Graph[int]] = []
    for g in (first, second):
        graph: nx.Graph[int] = nx.Graph()
        graph.add_nodes_from((i, {"c": colour}) for i, colour in enumerate(g.colours))
        graph.add_edges_from((e.low.index, e.high.index) for e in g.edges)
        graphs.append(graph)
    return bool(nx.vf2pp_is_isomorphic(graphs[0], graphs[1], node_label="c"))
