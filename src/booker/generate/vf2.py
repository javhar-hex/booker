"""
A slow graph-matching canonicalizer for a small executable sample, independent of
BLISS. Representatives are the first-discovered labelled states, so never use it on the
full atlas.
"""

from __future__ import annotations

import dataclasses as dc
from collections import Counter, defaultdict
from collections.abc import Iterable

import networkx as nx
from javhar_util.immutables import ZVec

from booker.core.model.state import State


@dc.dataclass(frozen=True, slots=True, order=True)
class TeamSignature:
    "What an isomorphism cannot change about one team."

    wins: int
    losses: int
    degree: int


Signature = ZVec[TeamSignature]

MAX_DEPTH = 6
"The deepest layer, counted in matches played, that is still small enough to use."


class VF2PrefixCanonicalizer:
    """
    Maps a state to the first state seen that is isomorphic to it, or to itself if it is
    the first of its kind. Remembering what it has seen is the point, not a shortcut:
    the representatives are whichever labelled states happened to come first.
    """

    def __init__(self, known: Iterable[State]) -> None:
        self._representatives: defaultdict[Signature, list[State]] = defaultdict(list)
        for state in known:
            self._representatives[_signature(state)].append(state)

    def __call__(self, state: State) -> State:
        graph = _graph(state)
        candidates = self._representatives[_signature(state)]
        for representative in candidates:
            if nx.is_isomorphic(graph, _graph(representative), node_match=_same_record):
                return representative
        candidates.append(state)
        return state


def _signature(state: State) -> Signature:
    degree = Counter(
        team for pairing in state.met for team in (pairing.low, pairing.high)
    )
    return ZVec(
        sorted(
            TeamSignature(wins=record.wins, losses=record.losses, degree=degree[team])
            for team, record in zip(state.teams, state.records)
        )
    )


def _graph(state: State) -> nx.Graph[int]:
    graph: nx.Graph[int] = nx.Graph()
    graph.add_nodes_from(
        (team.index, {"record": state.record(team)}) for team in state.teams
    )
    graph.add_edges_from(
        (pairing.low.index, pairing.high.index) for pairing in state.met
    )
    return graph


def _same_record(a: dict[str, object], b: dict[str, object]) -> bool:
    return a["record"] == b["record"]
