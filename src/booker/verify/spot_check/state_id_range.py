"""A range of the states of an atlas, by their ids."""

from __future__ import annotations

import dataclasses as dc

from booker.verify.spot_check.state_id import StateId


@dc.dataclass(frozen=True, slots=True)
class StateIdRange:
    "The states from `start` up to, not including, `stop`; `None` is unbounded."

    start: StateId | None = None
    stop: StateId | None = None

    @classmethod
    def of(cls, start: int | None = None, stop: int | None = None) -> StateIdRange:
        "From the numbers of the rows, as they come from the command line."
        return cls(
            start=None if start is None else StateId(value=start),
            stop=None if stop is None else StateId(value=stop),
        )

    def __str__(self) -> str:
        start = "start" if self.start is None else self.start
        stop = "end" if self.stop is None else self.stop
        return f"[{start}, {stop})"

    @property
    def start_value(self) -> int | None:
        "The number of the first row, or `None` where the range is unbounded."
        return None if self.start is None else self.start.value

    @property
    def stop_value(self) -> int | None:
        "The number of the row it stops before, or `None` where it is unbounded."
        return None if self.stop is None else self.stop.value
