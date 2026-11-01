"""State encoding and authoritative transition rules (generator side).

Only live teams appear. Their names are local vertex indices; isomorphic colored
simple graphs are identified with BLISS. Past repeats are NOT part of the state: each action has a local repeat cost,
and the minimax value counts only future repeats.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations

PLAYERS = 16


@dataclass(frozen=True)
class State:
    # (wins, losses) of active teams; losses are 0 or 1
    players: tuple[tuple[int, int], ...]
    # undirected simple graph: two ACTIVE teams have met at least once
    edges: tuple[tuple[int, int], ...]

    @property
    def depth(self) -> int:
        return 2 * (PLAYERS - len(self.players)) + sum(loss for _, loss in self.players)

    @property
    def terminal(self) -> bool:
        return len(self.players) == 1


def start() -> State:
    return State(((0, 0),) * PLAYERS, ())


def moves(state: State) -> list[tuple[int, int]]:
    """Every legal action in the unrestricted game, without round barriers."""
    if state.terminal:
        return []
    undefeated = sum(loss == 0 for _, loss in state.players)
    allowed = []
    for a, b in combinations(range(len(state.players)), 2):
        x, y = state.players[a], state.players[b]
        # The two exact rules in the paper. No viability oracle is needed.
        same_record = x == y and (x != (4, 1) or undefeated == 0)
        cross_bracket = undefeated == 1 and (
            (x[1] == 0 and y == (4, 1)) or (y[1] == 0 and x == (4, 1))
        )
        if same_record or cross_bracket:
            allowed.append((a, b))
    return allowed


def pairing_classes(state: State) -> list[tuple[tuple[int, int], int]]:
    """Legal pairings grouped into orbits under the automorphisms of the coloured graph.

    Returns (smallest pairing of the orbit, orbit size), sorted. Equivalent pairings
    lead to the same Collider-to-move state, so only one per orbit is expanded.
    """
    import igraph as ig

    legal = moves(state)
    g = ig.Graph(n=len(state.players), edges=list(state.edges), directed=False)
    root = {pair: pair for pair in legal}

    def find(pair: tuple[int, int]) -> tuple[int, int]:
        while root[pair] != pair:
            pair = root[pair]
        return pair

    # Linking the larger root under the smaller keeps each root the orbit minimum.
    for perm in g.automorphism_group(color=_colours(state)):
        for a, b in legal:
            x, y = find((a, b)), find((min(perm[a], perm[b]), max(perm[a], perm[b])))
            if x != y:
                root[max(x, y)] = min(x, y)
    return sorted(Counter(find(pair) for pair in legal).items())


def advance(state: State, winner: int, loser: int) -> tuple[State, int]:
    """Resolve one match; return (new state before canonicalization, repeat cost)."""
    assert 0 <= winner < len(state.players) and 0 <= loser < len(state.players)
    assert winner != loser
    assert tuple(sorted((winner, loser))) in moves(state)
    p = list(state.players)
    w, l = p[winner]
    p[winner] = (w + 1, l)
    w, l = p[loser]
    p[loser] = (w, l + 1)
    assert p[winner][0] <= 6
    assert p[loser][1] <= 2
    pair = tuple(sorted((winner, loser)))
    repeat = int(pair in state.edges)
    # Drop eliminated teams AND all edges incident to them.
    alive = [i for i, (_, losses) in enumerate(p) if losses < 2]
    remap = {old: new for new, old in enumerate(alive)}
    edges = set(state.edges)
    edges.add(pair)
    edges = tuple(
        sorted(
            tuple(sorted((remap[a], remap[b])))
            for a, b in edges
            if a in remap and b in remap
        )
    )
    child = State(tuple(p[i] for i in alive), edges)
    assert child.depth == state.depth + 1
    if child.terminal:
        assert child.players in (((6, 0),), ((6, 1),)), child
        assert child.depth in (30, 31), child
    else:
        assert all(w < 6 for w, _ in child.players)
    return child, repeat


def pack(state: State) -> bytes:
    """Stable format: [n, n*(2*w+loss), adjacency bitset].

    Adjacency bits are in lexicographic (i,j) order, i<j, little endian in each
    byte. Works for up to 16 living vertices. Versioned as schema v3 in SQLite.
    """
    n = len(state.players)
    assert 1 <= n <= PLAYERS
    codes = [2 * w + l for w, l in state.players]
    assert all(0 <= c <= 13 for c in codes)
    pair_set = set(state.edges)
    assert len(pair_set) == len(state.edges)
    for a, b in pair_set:
        assert 0 <= a < b < n
    mask = 0
    for k, (a, b) in enumerate(combinations(range(n), 2)):
        if (a, b) in pair_set:
            mask |= 1 << k
    return (
        bytes((n,)) + bytes(codes) + mask.to_bytes((n * (n - 1) // 2 + 7) // 8, "little")
    )


def unpack(data: bytes) -> State:
    n = data[0]
    assert 1 <= n <= PLAYERS
    count = n * (n - 1) // 2
    assert len(data) == 1 + n + (count + 7) // 8
    codes = data[1 : 1 + n]
    p = tuple((c // 2, c % 2) for c in codes)
    mask = int.from_bytes(data[1 + n :], "little")
    assert mask >> count == 0
    edges = tuple(
        pair for k, pair in enumerate(combinations(range(n), 2)) if (mask >> k) & 1
    )
    return State(p, edges)


def canonical(state: State) -> State:
    """Canonical colored graph via igraph/BLISS, using (wins,losses) as colors.

    IMPORTANT: preserve the vertex 'wl' attribute through permute_vertices;
    relying on whether the permutation is old->new or new->old is error prone.
    """
    import igraph as ig

    n = len(state.players)
    g = ig.Graph(n=n, edges=list(state.edges), directed=False)
    g.vs["wl"] = _colours(state)
    permutation = g.canonical_permutation(color=g.vs["wl"])
    cg = g.permute_vertices(permutation)
    players = tuple((code // 2, code % 2) for code in cg.vs["wl"])
    edges = tuple(sorted(tuple(sorted(edge)) for edge in cg.get_edgelist()))
    return State(players, edges)


def _colours(state: State) -> list[int]:
    return [2 * w + l for w, l in state.players]
