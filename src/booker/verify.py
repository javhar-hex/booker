"""Independent SQLite audit. Does NOT import generator, state, or storage.

Reimplements legality, child construction, and Bellman backup. Checks successors
by a *different* graph-isomorphism algorithm (VF2), rather than trusting the
BLISS canonicalization used by the generator. Likewise checks, by VF2 on graphs with
the paired teams marked, that the stored pairings are exactly one per orbit of the
legal pairings under the state's automorphisms, with the correct orbit sizes.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sqlite3
from functools import lru_cache


def parse(blob):
    n = blob[0]
    assert 1 <= n <= 16
    nbits = n * (n - 1) // 2
    assert len(blob) == 1 + n + (nbits + 7) // 8, (n, len(blob))
    codes = blob[1 : 1 + n]
    assert all(0 <= x <= 13 for x in codes)
    players = tuple((c // 2, c % 2) for c in codes)
    assert all(w <= 6 and loss <= 1 for w, loss in players)
    adjacency = int.from_bytes(blob[1 + n :], "little")
    assert adjacency >> nbits == 0
    edges = set()
    for i, (a, b) in enumerate(itertools.combinations(range(n), 2)):
        if adjacency & (1 << i):
            edges.add((a, b))
    return players, edges


# Independently implement the two admissibility rules from the paper.
# This module deliberately imports none of the generator-side code.
def legal(players):
    if len(players) == 1:
        return set()
    undefeated = sum(loss == 0 for _, loss in players)
    pairs = set()
    for i, j in itertools.combinations(range(len(players)), 2):
        x, y = players[i], players[j]
        if x == y:
            if x != (4, 1) or undefeated == 0:
                pairs.add((i, j))
        elif undefeated == 1 and (
            (x[1] == 0 and y == (4, 1)) or (y[1] == 0 and x == (4, 1))
        ):
            pairs.add((i, j))
    return pairs


def outcome(players, edges, winner, loser):
    pair = tuple(sorted((winner, loser)))
    cost = int(pair in edges)
    p = list(players)
    p[winner] = (p[winner][0] + 1, p[winner][1])
    p[loser] = (p[loser][0], p[loser][1] + 1)
    survivor = [i for i, (_, l) in enumerate(p) if l < 2]
    ix = {old: new for new, old in enumerate(survivor)}
    child_edges = {
        (min(ix[a], ix[b]), max(ix[a], ix[b]))
        for a, b in edges | {pair}
        if a in ix and b in ix
    }
    return tuple(p[i] for i in survivor), child_edges, cost


def coloured_isomorphic(c1, e1, c2, e2, mode):
    if len(c1) != len(c2) or sorted(c1) != sorted(c2) or len(e1) != len(e2):
        return False
    if mode == "igraph":
        import igraph as ig

        g = ig.Graph(n=len(c1), edges=list(e1))
        h = ig.Graph(n=len(c2), edges=list(e2))
        return bool(g.isomorphic_vf2(h, color1=list(c1), color2=list(c2)))
    import networkx as nx

    g = nx.Graph()
    h = nx.Graph()
    g.add_nodes_from((i, {"c": c}) for i, c in enumerate(c1))
    h.add_nodes_from((i, {"c": c}) for i, c in enumerate(c2))
    g.add_edges_from(e1)
    h.add_edges_from(e2)
    return nx.vf2pp_is_isomorphic(g, h, node_label="c")


def isomorphic(x, y, mode):
    (p1, e1), (p2, e2) = x, y
    return coloured_isomorphic(
        [2 * w + l for w, l in p1], e1, [2 * w + l for w, l in p2], e2, mode
    )


def equivalent_pairs(players, edges, x, y, mode):
    """Is there an automorphism of (players,edges) mapping pair x onto pair y?"""
    if (x in edges) != (y in edges):
        return False

    def marked(pair):
        return [2 * (2 * w + l) + (i in pair) for i, (w, l) in enumerate(players)]

    return coloured_isomorphic(marked(x), edges, marked(y), edges, mode)


def check_orbits(players, edges, rows, mode):
    """Each legal pairing is equivalent to exactly one stored pairing, whose class_size
    is the number of legal pairings equivalent to it."""
    reps = {(a, b): size for a, b, _, _, _, size, _ in rows}
    hits = dict.fromkeys(reps, 0)
    for pair in legal(players):
        matches = [
            rep for rep in reps if equivalent_pairs(players, edges, pair, rep, mode)
        ]
        assert len(matches) == 1, ("orbit representatives", players, pair, matches)
        hits[matches[0]] += 1
    assert hits == reps, ("orbit sizes", players, hits, reps)


CHECKPOINT_EVERY = 1000


def load_checkpoint(checkpoint, scope):
    """Progress saved by an earlier run of the same scope, or None to start afresh."""
    if checkpoint is None or not os.path.exists(checkpoint):
        return None
    with open(checkpoint) as f:
        progress = json.load(f)
    assert progress["scope"] == scope, (
        "checkpoint is for another run",
        progress["scope"],
        scope,
    )
    return progress


def save_checkpoint(checkpoint, progress):
    tmp = checkpoint + ".tmp"
    with open(tmp, "w") as f:
        json.dump(progress, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, checkpoint)


def audit(
    path: str,
    mode: str = "networkx",
    limit: int = 0,
    expect_root: int | None = None,
    require_complete: bool = False,
    from_id: int | None = None,
    to_id: int | None = None,
    checkpoint: str | None = None,
) -> None:
    """Check the states with from_id <= id < to_id (None = unbounded) and their actions.

    Whole-database checks run only in the range that starts at the beginning, so a set
    of ranges partitioning the ids checks everything exactly once.

    With a checkpoint file, progress is saved every CHECKPOINT_EVERY states and a rerun
    resumes after the last saved state. The whole-database checks are cheap and simply
    run again on resume.
    """
    scope = {
        "db": os.path.abspath(path),
        "mode": mode,
        "from_id": from_id,
        "to_id": to_id,
    }
    progress = load_checkpoint(checkpoint, scope) or {
        "scope": scope,
        "next_id": from_id if from_id is not None else -1,
        "states": 0,
        "actions": 0,
        "pairings": 0,
    }
    whole_database = from_id is None
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.execute("PRAGMA foreign_keys=ON")
    metadata = dict(con.execute("SELECT key,value FROM meta"))
    assert metadata["schema_version"] == "5"
    assert metadata["game"] == "unrestricted-16-2-6"
    root = int(metadata["root_id"])

    @lru_cache(maxsize=65536)
    def fetch(sid):
        row = con.execute(
            "SELECT key,depth,active,value,expanded FROM states WHERE id=?", (sid,)
        ).fetchone()
        assert row is not None, sid
        return parse(row[0]), row[1:]

    nchecked = progress["states"]
    n_actions = progress["actions"]
    n_pairings = progress["pairings"]
    if nchecked:
        print(
            f"resuming at id {progress['next_id']} after {nchecked:,} states", flush=True
        )
    solved = True
    unexpanded = con.execute("SELECT count(*) FROM states WHERE expanded=0").fetchone()[
        0
    ]
    unsolved = con.execute(
        "SELECT (SELECT count(*) FROM states WHERE value IS NULL)"
        "+(SELECT count(*) FROM actions WHERE value IS NULL)"
    ).fetchone()[0]
    if require_complete and whole_database:
        assert not unexpanded and not unsolved, (unexpanded, unsolved)
        last = con.execute("SELECT MAX(depth) FROM states").fetchone()[0]
        assert last == 31, ("last match is missing", last)
        terminal_records = con.execute(
            "SELECT key,depth FROM states WHERE active=1"
        ).fetchall()
        assert len(terminal_records) == 2, (
            "expected exactly two terminal states",
            len(terminal_records),
        )
        expected = {(((6, 0),), 30), (((6, 1),), 31)}
        got = {(parse(blob)[0], d) for blob, d in terminal_records}
        assert got == expected, ("incorrect terminal states", got)
    solved = not unsolved
    if whole_database:
        root_state, _ = fetch(root)
        assert root_state == (((0, 0),) * 16, set()), "Wrong initial position"
        assert (
            con.execute("SELECT count(*) FROM states WHERE depth=0").fetchone()[0] == 1
        )
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not con.execute("PRAGMA foreign_key_check").fetchone()
    # A strict depth-increasing DAG with no non-root sources is necessarily
    # wholly rooted at the initial state (rules out extra disconnected states).
    if whole_database and not limit:
        orphan = con.execute(
            """
          SELECT s.id FROM states s WHERE s.id!=? AND NOT EXISTS (
            SELECT 1 FROM actions a WHERE a.a_wins=s.id OR a.b_wins=s.id
          ) LIMIT 1
        """,
            (root,),
        ).fetchone()
        assert orphan is None, ("orphan state", orphan)
    bounds = (progress["next_id"], to_id if to_id is not None else 2**62)
    for (sid,) in con.execute(
        "SELECT id FROM states WHERE id>=? AND id<? ORDER BY id", bounds
    ):
        (p, e), (d, nactive, v, expanded) = fetch(sid)
        assert nactive == len(p) and 0 <= d <= 31
        assert d == 2 * (16 - nactive) + sum(l for _, l in p), (sid, d)
        if len(p) == 1:
            assert p in (((6, 0),), ((6, 1),)) and expanded
            assert d == (30 if p[0] == (6, 0) else 31)
        else:
            assert all(w < 6 for w, _ in p)
        # An edge cannot connect two unbeaten teams: one must have lost that meeting.
        assert all(not (p[a][1] == p[b][1] == 0) for a, b in e)
        rows = con.execute(
            "SELECT a,b,repeat_cost,a_wins,b_wins,class_size,value FROM actions WHERE parent=? ORDER BY a,b",
            (sid,),
        ).fetchall()
        pairs = {(a, b) for a, b, *_ in rows}
        assert len(pairs) == len(rows)
        if expanded:
            assert pairs <= legal(p), (sid, pairs - legal(p))
            check_orbits(p, e, rows, mode)
            assert (len(rows) == 0) == (len(p) == 1), (
                "nonterminal dead end / terminal with moves",
                sid,
            )
        else:
            assert not rows
        if solved:
            assert v is not None
            if len(p) == 1:
                assert v == 0
        opts = []
        for a, b, cost, ca, cb, size, cv in rows:
            expected_a = outcome(p, e, a, b)
            expected_b = outcome(p, e, b, a)
            assert expected_a[2] == expected_b[2] == cost
            sa, _ = fetch(ca)
            sb, _ = fetch(cb)
            assert isomorphic(expected_a[:2], sa, mode), (sid, a, b, ca, "a")
            assert isomorphic(expected_b[:2], sb, mode), (sid, a, b, cb, "b")
            assert 2 * (16 - len(sa[0])) + sum(l for _, l in sa[0]) == d + 1
            assert 2 * (16 - len(sb[0])) + sum(l for _, l in sb[0]) == d + 1
            if solved:
                va = fetch(ca)[1][2]
                vb = fetch(cb)[1][2]
                assert cv == max(va, vb), ("Collider value", sid, a, b, cv, va, vb)
                opts.append(cost + cv)
            n_actions += 1
            n_pairings += size
        if solved and rows:
            assert v == min(opts), (sid, v, min(opts))
        nchecked += 1
        if checkpoint and (nchecked % CHECKPOINT_EVERY == 0 or nchecked == limit):
            save_checkpoint(
                checkpoint,
                {
                    **progress,
                    "next_id": sid + 1,
                    "states": nchecked,
                    "actions": n_actions,
                    "pairings": n_pairings,
                },
            )
        if limit and nchecked >= limit:
            break
        if nchecked % 10000 == 0:
            print(f"checked {nchecked:,} states, {n_actions:,} actions", flush=True)
    if expect_root is not None and whole_database:
        rv = fetch(root)[1][2]
        assert rv == expect_root, (rv, expect_root)
    print(
        f"PASS: ids [{from_id}, {to_id}): checked {nchecked:,} states / {n_actions:,} actions "
        f"({n_pairings:,} labelled pairings) "
        f"with independent {mode.upper()} isomorphism, solved={solved}, "
        f"unexpanded={unexpanded:,}"
    )
    con.close()


def main():
    p = argparse.ArgumentParser(
        description="Independent position/transition/minimax verifier"
    )
    p.add_argument("db")
    p.add_argument("--mode", choices=("igraph", "networkx"), default="networkx")
    p.add_argument(
        "--limit", type=int, default=0, help="Number of states to check (0=all)"
    )
    p.add_argument("--require-complete", action="store_true")
    p.add_argument("--expect-root", type=int)
    p.add_argument(
        "--from-id",
        type=int,
        help="First state id to check (inclusive); "
        "whole-database checks run only when omitted",
    )
    p.add_argument("--to-id", type=int, help="State id to stop before (exclusive)")
    p.add_argument(
        "--checkpoint", help="Progress file: saved periodically, resumed from if present"
    )
    a = p.parse_args()
    audit(
        a.db,
        a.mode,
        a.limit,
        a.expect_root,
        a.require_complete,
        a.from_id,
        a.to_id,
        a.checkpoint,
    )


if __name__ == "__main__":
    main()
