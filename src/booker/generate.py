"""Generator and retrograde minimax solver. No verifier code is imported."""
from __future__ import annotations
import argparse
import sqlite3
from pathlib import Path

from .state import advance, canonical, pack, pairing_classes, start, unpack
from collections import defaultdict
from .storage import add_state, connect, init


class VF2PrefixCanonicalizer:
    """Slow graph-match fallback for a small executable sample.

    Representatives are first-discovered labeled states; never use on full atlas.
    """
    def __init__(self, con):
        import networkx as nx
        self.nx=nx
        self.reps=defaultdict(list)
        for (blob,) in con.execute("SELECT key FROM states"):
            s=unpack(blob)
            self.reps[self.signature(s)].append(s)

    def signature(self,s):
        deg=[0]*len(s.players)
        for a,b in s.edges: deg[a]+=1;deg[b]+=1
        return (tuple(sorted(s.players)),
                tuple(sorted((p,deg[i]) for i,p in enumerate(s.players))))

    def __call__(self,s):
        from .state import State
        nx=self.nx
        def graph(t):
            g=nx.Graph()
            g.add_nodes_from((i,{"wl":p}) for i,p in enumerate(t.players))
            g.add_edges_from(t.edges)
            return g
        sig=self.signature(s)
        if sig not in self.reps:
            self.reps[sig].append(s)
            return s
        g=graph(s)
        for rep in self.reps[sig]:
            if nx.is_isomorphic(g,graph(rep),node_match=lambda a,b:a["wl"]==b["wl"]):
                return rep
        self.reps[sig].append(s)
        return s


def generate(path: str, max_depth: int=31, backend: str='bliss') -> None:
    assert 0 <= max_depth <= 31
    if backend=='vf2' and max_depth > 6:
        raise ValueError("VF2 fallback is for a six-match prefix only; use BLISS for full generation")
    con = connect(path)
    init(con)
    con.execute("PRAGMA journal_mode=WAL")
    prior = con.execute("SELECT value FROM meta WHERE key='backend'").fetchone()
    if prior and prior[0]!=backend:
        raise ValueError(f"Cannot resume {prior[0]} atlas using {backend} canonicalization")
    with con:
        con.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('backend',?)",(backend,))
    canon = canonical if backend=='bliss' else VF2PrefixCanonicalizer(con)
    with con:
        root = add_state(con, canon(start()))
        con.execute("INSERT OR IGNORE INTO meta(key,value) VALUES ('root_id',?)",(str(root),))
    for depth in range(max_depth):
        rows = con.execute("SELECT id,key FROM states WHERE depth=? AND expanded=0 ORDER BY id",
                           (depth,)).fetchall()
        if not rows:
            continue
        print(f"expanding depth {depth:02d}: {len(rows):,} states",flush=True)
        # One depth is atomic; interruption never leaves a half-expanded layer.
        with con:
            for sid, data in rows:
                state = unpack(data)
                if state.terminal:
                    con.execute("UPDATE states SET expanded=1 WHERE id=?",(sid,))
                    continue
                for (a,b), size in pairing_classes(state):
                    ca,cost_a = advance(state,a,b)
                    cb,cost_b = advance(state,b,a)
                    assert cost_a == cost_b
                    aid = add_state(con,canon(ca))
                    bid = add_state(con,canon(cb))
                    con.execute("INSERT INTO actions(parent,a,b,repeat_cost,class_size,a_wins,b_wins) "
                                "VALUES (?,?,?,?,?,?,?)",(sid,a,b,cost_a,size,aid,bid))
                con.execute("UPDATE states SET expanded=1 WHERE id=?",(sid,))
    # Mark remaining terminal states expanded, even for max_depth=31.
    with con:
        con.execute("UPDATE states SET expanded=1 WHERE active=1")
    print("states:",con.execute("SELECT COUNT(*) FROM states").fetchone()[0],
          "actions:",con.execute("SELECT COUNT(*) FROM actions").fetchone()[0])
    con.close()


def solve(path: str) -> None:
    con = connect(path)
    n = con.execute("SELECT count(*) FROM states WHERE expanded=0").fetchone()[0]
    if n:
        raise RuntimeError(f"Cannot solve truncated atlas: {n:,} unexpanded states")
    with con:
        con.execute("UPDATE actions SET value=NULL")
        con.execute("UPDATE states SET value=NULL")
        con.execute("UPDATE states SET value=0 WHERE active=1")
    # Children of a depth-d state's Collider rows are at depth d+1, solved one pass earlier.
    for depth in range(31,-1,-1):
        with con:
            con.execute("""
                UPDATE actions SET value=(
                  SELECT MAX(c1.value,c2.value) FROM states c1, states c2
                  WHERE c1.id=actions.a_wins AND c2.id=actions.b_wins
                ) WHERE parent IN (SELECT id FROM states WHERE depth=?)
            """,(depth,))
            con.execute("""
                UPDATE states SET value=(
                  SELECT MIN(repeat_cost + value) FROM actions WHERE parent=states.id
                ) WHERE depth=? AND active>1
            """,(depth,))
        n = con.execute("""
            SELECT (SELECT count(*) FROM states WHERE depth=?1 AND value IS NULL)
                 + (SELECT count(*) FROM actions WHERE value IS NULL
                    AND parent IN (SELECT id FROM states WHERE depth=?1))
        """,(depth,)).fetchone()[0]
        if n:
            raise RuntimeError(f"Bellman backup missing {n} values at depth {depth}")
    with con:
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('solved','true')")
    rid = int(con.execute("SELECT value FROM meta WHERE key='root_id'").fetchone()[0])
    value = con.execute("SELECT value FROM states WHERE id=?",(rid,)).fetchone()[0]
    print(f"root minimax value: {value}")
    con.close()


def stats(path: str):
    con = connect(path)
    print("depth  states  collider  pairings  min-value  max-value")
    for k,n,c,m,mi,ma in con.execute("""
       SELECT s.depth, COUNT(DISTINCT s.id), COUNT(a.a), COALESCE(SUM(a.class_size),0),
              MIN(s.value), MAX(s.value)
       FROM states s LEFT JOIN actions a ON a.parent=s.id
       GROUP BY s.depth ORDER BY s.depth
    """):
        print(f"{k:>5} {n:>7,} {c:>9,} {m:>9,} {str(mi):>10} {str(ma):>10}")
    con.close()


def main():
    p=argparse.ArgumentParser(description="Unrestricted (16,2,6) Scheduler-Collider atlas")
    sub=p.add_subparsers(dest="mode",required=True)
    gen=sub.add_parser("generate"); gen.add_argument("db"); gen.add_argument("--max-depth",type=int,default=31); gen.add_argument("--backend",choices=("bliss","vf2"),default="bliss")
    sub.add_parser("solve").add_argument("db")
    sub.add_parser("stats").add_argument("db")
    args=p.parse_args()
    if args.mode=="generate": generate(args.db,args.max_depth,args.backend)
    elif args.mode=="solve": solve(args.db)
    else: stats(args.db)

if __name__ == "__main__": main()
