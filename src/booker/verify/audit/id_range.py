"""A range of state ids."""

from __future__ import annotations

import dataclasses as dc


@dc.dataclass(frozen=True, slots=True)
class IdRange:
    "The state ids from `start` up to, not including, `stop`; `None` is unbounded."

    start: int | None = None
    stop: int | None = None

    def __str__(self) -> str:
        start = "start" if self.start is None else self.start
        stop = "end" if self.stop is None else self.stop
        return f"[{start}, {stop})"
