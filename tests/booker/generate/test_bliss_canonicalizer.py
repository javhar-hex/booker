"""The canonical state by BLISS: equal exactly for isomorphic states."""

from __future__ import annotations

import random
from collections.abc import Callable, Iterator

import networkx as nx

from booker.core.model.state import State
from booker.core.symmetry.relabelling import Relabelling
from booker.generate.bliss_canonicalizer import BlissCanonicalizer
from booker.generate.state_canonicalizer import StateCanonicalizer

CANONICALIZER = BlissCanonicalizer()


def _graph(state: State) -> nx.Graph[int]:
    graph: nx.Graph[int] = nx.Graph()
    graph.add_nodes_from(
        (team.index, {"record": state.record(team)}) for team in state.teams
    )
    graph.add_edges_from(
        (pairing.lhs.index, pairing.rhs.index) for pairing in state.past_pairings
    )
    return graph


def test_declares_that_it_implements_the_protocol() -> None:
    assert StateCanonicalizer in BlissCanonicalizer.__mro__


def test_is_isomorphic_to_the_original_by_networkx(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    "An oracle independent of igraph/BLISS, which the canonical form is built on."
    rng = random.Random(0)
    same_record = nx.algorithms.isomorphism.categorical_node_match("record", None)

    for state in (state for _ in range(20) for state in play_game(rng)):
        assert nx.is_isomorphic(
            _graph(CANONICALIZER(state)), _graph(state), node_match=same_record
        )


def test_a_state_and_a_relabelling_of_it_have_the_same_canonical_state(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    rng = random.Random(5)

    for state in (state for _ in range(20) for state in play_game(rng)):
        indices = list(range(state.size))
        rng.shuffle(indices)
        shuffled = Relabelling.of(indices).state(state)

        assert CANONICALIZER(shuffled) == CANONICALIZER(state)


def test_the_canonical_state_is_its_own_canonical_state(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    for state in play_game(random.Random(2)):
        assert CANONICALIZER(CANONICALIZER(state)) == CANONICALIZER(state)
