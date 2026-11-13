"""A range of the states of an atlas, by their ids."""

from __future__ import annotations

import dataclasses as dc

from booker.verify.spot_check.state_id import StateId


@dc.dataclass(frozen=True, slots=True)
class StateIdRange:
    "The states from `start` up to, not including, `stop`; `None` is unbounded."

    start: StateId | None = None
    stop: StateId | None = None

    def __str__(self) -> str:
        start = "start" if self.start is None else self.start
        stop = "end" if self.stop is None else self.stop
        return f"[{start}, {stop})"
