"""
Solving an atlas by retrograde analysis: from its last layer back to its root, where a
search would go forward. A Collider position is worth the larger of its two children, and a
Scheduler position the least, over its actions, of what the action costs and is worth.
"""

from __future__ import annotations

import dataclasses as dc
import sqlite3


@dc.dataclass(frozen=True, slots=True)
class AtlasRetrogradeSolver:
    """
    The steps of the retrograde analysis that solves an atlas, which `solve` puts in order.
    Obtain one with `Atlas.retrograde_solver`. Each statement commits itself, and `solve`
    begins with `reset_values`, so that a stop in the middle costs nothing.
    """

    connection: sqlite3.Connection

    def reset_values(self) -> None:
        "Forget every value but the decided positions', which are worth nothing more."
        self.connection.execute("UPDATE actions SET value=NULL")
        self.connection.execute("UPDATE states SET value=NULL")
        self.connection.execute("UPDATE states SET value=0 WHERE active=1")

    def back_up(self, depth: int) -> None:
        "Values the positions at `depth` from their children, which are at `depth + 1`."
        self.connection.execute(
            """
            UPDATE actions SET value=(
              SELECT MAX(c1.value,c2.value) FROM states c1, states c2
              WHERE c1.id=actions.a_wins AND c2.id=actions.b_wins
            ) WHERE parent IN (SELECT id FROM states WHERE depth=?)
            """,
            (depth,),
        )
        self.connection.execute(
            """
            UPDATE states SET value=(
              SELECT MIN(repeat_cost + value) FROM actions WHERE parent=states.id
            ) WHERE depth=? AND active>1
            """,
            (depth,),
        )

    def num_unvalued(self, depth: int) -> int:
        count: int = self.connection.execute(
            """
            SELECT (SELECT COUNT(*) FROM states WHERE depth=? AND value IS NULL)
                 + (SELECT COUNT(*) FROM actions WHERE value IS NULL
                    AND parent IN (SELECT id FROM states WHERE depth=?))
            """,
            (depth, depth),
        ).fetchone()[0]
        return count

    def mark_solved(self) -> None:
        self.connection.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES ('solved','true')"
        )

    def root_value(self) -> int:
        row = self.connection.execute(
            "SELECT value FROM states WHERE id="
            "(SELECT CAST(value AS INTEGER) FROM meta WHERE key='root_id')"
        ).fetchone()
        if row is None or row[0] is None:
            raise ValueError("the atlas has no solved root")
        value: int = row[0]
        return value
