"""
Whether two coloured graphs are alike, by VF2. The generator canonicalizes with BLISS;
this is a different algorithm, which is the point.
"""

from __future__ import annotations

import dataclasses as dc
import enum

import igraph as ig
import networkx as nx
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.invariants import ELIMINATION_LOSSES
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State


class Mode(enum.Enum):
    "Which library's VF2 does the comparing."

    IGRAPH = "igraph"
    NETWORKX = "networkx"


IGRAPH = Mode.IGRAPH
NETWORKX = Mode.NETWORKX


@dc.dataclass(frozen=True, slots=True)
class ColouredGraph:
    colours: ZVec[int]
    edges: ZSet[Pairing]

    @classmethod
    def of(cls, state: State) -> ColouredGraph:
        "Teams coloured by record, adjacent when they have met."
        return cls(
            colours=ZVec(_colour(record) for record in state.records), edges=state.met
        )

    @classmethod
    def marked(cls, state: State, pairing: Pairing) -> ColouredGraph:
        "The state's graph, with the two teams of `pairing` set apart by colour."
        return cls(
            colours=ZVec(
                2 * _colour(state.record(team)) + pairing.involves(team)
                for team in state.teams
            ),
            edges=state.met,
        )


def are_isomorphic(first: ColouredGraph, second: ColouredGraph, mode: Mode) -> bool:
    if (
        len(first.colours) != len(second.colours)
        or sorted(first.colours) != sorted(second.colours)
        or len(first.edges) != len(second.edges)
    ):
        return False
    if mode is Mode.IGRAPH:
        return _igraph_isomorphic(first, second)
    else:
        return _networkx_isomorphic(first, second)


def _colour(record: Record) -> int:
    return record.wins * ELIMINATION_LOSSES + record.losses


def _igraph_isomorphic(first: ColouredGraph, second: ColouredGraph) -> bool:
    graphs = [
        ig.Graph(n=len(g.colours), edges=[(e.low.index, e.high.index) for e in g.edges])
        for g in (first, second)
    ]
    return bool(
        graphs[0].isomorphic_vf2(
            graphs[1], color1=list(first.colours), color2=list(second.colours)
        )
    )


def _networkx_isomorphic(first: ColouredGraph, second: ColouredGraph) -> bool:
    graphs: list[nx.Graph[int]] = []
    for g in (first, second):
        graph: nx.Graph[int] = nx.Graph()
        graph.add_nodes_from((i, {"c": colour}) for i, colour in enumerate(g.colours))
        graph.add_edges_from((e.low.index, e.high.index) for e in g.edges)
        graphs.append(graph)
    return bool(nx.vf2pp_is_isomorphic(graphs[0], graphs[1], node_label="c"))
