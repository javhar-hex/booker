"""Canonical keys must identify exactly the isomorphism classes of coloured graphs.

Isomorphic states are checked with networkx VF2, independently of the igraph/BLISS
canonicalization under test.
"""

from __future__ import annotations

import random

import networkx as nx
import pytest

from booker.state import State, advance, canonical, moves, pack, start, unpack

SEEDS = range(200)


def _random_state(rng: random.Random) -> State:
    state = start()
    for _ in range(rng.randrange(31)):
        a, b = rng.choice(moves(state))
        winner, loser = (a, b) if rng.random() < 0.5 else (b, a)
        state, _ = advance(state, winner, loser)
    return state


def _shuffled(state: State, rng: random.Random) -> State:
    new_of_old = rng.sample(range(len(state.players)), len(state.players))
    players = tuple(p for _, p in sorted(zip(new_of_old, state.players)))
    relabeled = ((new_of_old[a], new_of_old[b]) for a, b in state.edges)
    edges = tuple(sorted((min(a, b), max(a, b)) for a, b in relabeled))
    return State(players, edges)


def _isomorphic(x: State, y: State) -> bool:
    def graph(state: State) -> nx.Graph[int]:
        g: nx.Graph[int] = nx.Graph()
        g.add_nodes_from((i, {"record": p}) for i, p in enumerate(state.players))
        g.add_edges_from(state.edges)
        return g

    same_record = nx.algorithms.isomorphism.categorical_node_match("record", None)
    return bool(nx.is_isomorphic(graph(x), graph(y), node_match=same_record))


@pytest.mark.parametrize("seed", SEEDS)
def test_canonical_is_invariant_under_relabeling(seed: int) -> None:
    rng = random.Random(seed)
    state = _random_state(rng)
    assert canonical(_shuffled(state, rng)) == canonical(state)


@pytest.mark.parametrize("seed", SEEDS)
def test_canonical_is_isomorphic_to_the_original(seed: int) -> None:
    state = _random_state(random.Random(seed))
    assert _isomorphic(canonical(state), state)


@pytest.mark.parametrize("seed", SEEDS)
def test_canonical_is_idempotent(seed: int) -> None:
    once = canonical(_random_state(random.Random(seed)))
    assert canonical(once) == once


def test_canonical_distinguishes_graph_shape() -> None:
    records = ((1, 1),) * 4
    path = State(records, ((0, 1), (1, 2), (2, 3)))
    star = State(records, ((0, 1), (0, 2), (0, 3)))
    assert canonical(path) != canonical(star)


def test_canonical_distinguishes_colouring_of_the_same_shape() -> None:
    records = ((1, 0), (0, 1), (0, 1))
    winner_at_end = State(records, ((0, 1), (1, 2)))
    winner_in_middle = State(records, ((0, 1), (0, 2)))
    assert canonical(winner_at_end) != canonical(winner_in_middle)


@pytest.mark.parametrize("seed", SEEDS)
def test_pack_round_trips(seed: int) -> None:
    state = canonical(_random_state(random.Random(seed)))
    assert unpack(pack(state)) == state
