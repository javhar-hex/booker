"""What to audit, and what an audit found."""

from __future__ import annotations

import dataclasses as dc

from booker.core.symmetry.kinds import SymmetryKind


@dc.dataclass(frozen=True, slots=True)
class IdRange:
    "The state ids from `start` up to, not including, `stop`; `None` is unbounded."

    start: int | None = None
    stop: int | None = None

    def __str__(self) -> str:
        start = "start" if self.start is None else self.start
        stop = "end" if self.stop is None else self.stop
        return f"[{start}, {stop})"


@dc.dataclass(frozen=True, slots=True)
class AuditPlan:
    """
    The checks on the states in `ids` and their actions. Whole-database checks run only
    in the range that starts at the beginning, so a set of ranges partitioning the ids
    checks everything exactly once. With `limit`, at most that many states in all are
    checked, counting those of earlier sittings resumed from `checkpoint`.

    Whether the stored children and pairings are the right ones is checked cheaply, by
    what a state's records and meetings must add up to. With `strict`, every child is also
    compared with the successor it should be, and every orbit found again, by that
    implementation of the symmetries of states: slow, and a check of the generator.
    """

    db: str
    ids: IdRange = IdRange()
    strict: SymmetryKind | None = None
    limit: int | None = None
    expect_root: int | None = None
    require_complete: bool = False
    checkpoint: str | None = None

    @property
    def is_whole_database(self) -> bool:
        return self.ids.start is None


@dc.dataclass(frozen=True, slots=True)
class AuditReport:
    ids: IdRange
    strict: SymmetryKind | None
    states: int
    actions: int
    pairings: int
    is_solved: bool
    unexpanded: int

    def __str__(self) -> str:
        how = (
            "children and orbits not compared"
            if self.strict is None
            else f"children and orbits compared by {self.strict.value}"
        )
        return (
            f"PASS: ids {self.ids}: checked {self.states:,} states / {self.actions:,} "
            f"actions ({self.pairings:,} labelled pairings), {how}, "
            f"solved={self.is_solved}, unexpanded={self.unexpanded:,}"
        )
