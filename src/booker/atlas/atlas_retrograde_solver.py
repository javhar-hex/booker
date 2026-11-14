"""
Solving an atlas by retrograde analysis: from its last layer back to its root, where a
search would go forward. A Collider position is worth the larger of its two children, and a
Scheduler position the least, over its actions, of what the action costs and is worth.
"""

from __future__ import annotations

import dataclasses as dc
import sqlite3

from booker.atlas.schema import ROOT_ID_META_KEY, SOLVED_META_KEY, SOLVED_META_VALUE


@dc.dataclass(frozen=True, slots=True)
class AtlasRetrogradeSolver:
    """
    The steps of the retrograde analysis that solves an atlas, which `solve` puts in order.
    Obtain one with `Atlas.retrograde_solver`. Each statement commits itself, and `solve`
    begins with `reset_gtvs`, so that a stop in the middle costs nothing.
    """

    connection: sqlite3.Connection

    def reset_gtvs(self) -> None:
        "Forget every GTV but the leaf positions, which are worth nothing more."
        self.connection.execute("UPDATE actions SET gtv=NULL")
        self.connection.execute("UPDATE states SET gtv=NULL")
        self.connection.execute("UPDATE states SET gtv=0 WHERE active=1")

    def back_up(self, depth: int) -> None:
        "Backs up the GTVs of the positions at `depth` from their children, at `depth + 1`."
        self.connection.execute(
            """
            UPDATE actions SET gtv=(
              SELECT MAX(lhs_child.gtv, rhs_child.gtv)
              FROM states lhs_child, states rhs_child
              WHERE lhs_child.id=actions.lhs_wins AND rhs_child.id=actions.rhs_wins
            ) WHERE parent IN (SELECT id FROM states WHERE depth=?)
            """,
            (depth,),
        )
        self.connection.execute(
            """
            UPDATE states SET gtv=(
              SELECT MIN(repeat_cost + gtv) FROM actions WHERE parent=states.id
            ) WHERE depth=? AND active>1
            """,
            (depth,),
        )

    def num_unsolved(self, depth: int) -> int:
        count: int = self.connection.execute(
            """
            SELECT (SELECT COUNT(*) FROM states WHERE depth=? AND gtv IS NULL)
                 + (SELECT COUNT(*) FROM actions WHERE gtv IS NULL
                    AND parent IN (SELECT id FROM states WHERE depth=?))
            """,
            (depth, depth),
        ).fetchone()[0]
        return count

    def mark_solved(self) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
            (SOLVED_META_KEY, SOLVED_META_VALUE),
        )

    def root_gtv(self) -> int:
        row = self.connection.execute(
            "SELECT gtv FROM states WHERE id="
            "(SELECT CAST(value AS INTEGER) FROM meta WHERE key=?)",
            (ROOT_ID_META_KEY,),
        ).fetchone()
        if row is None or row[0] is None:
            raise ValueError("the atlas has no solved root")
        gtv: int = row[0]
        return gtv
