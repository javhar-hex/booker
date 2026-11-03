"""What to audit, and what an audit found."""

from __future__ import annotations

import dataclasses as dc

from booker.verify.isomorphism import Mode


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
    """

    db: str
    mode: Mode
    ids: IdRange = IdRange()
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
    mode: Mode
    states: int
    actions: int
    pairings: int
    is_solved: bool
    unexpanded: int

    def __str__(self) -> str:
        return (
            f"PASS: ids {self.ids}: checked {self.states:,} states / {self.actions:,} "
            f"actions ({self.pairings:,} labelled pairings) with independent "
            f"{self.mode.value.upper()} isomorphism, solved={self.is_solved}, "
            f"unexpanded={self.unexpanded:,}"
        )
