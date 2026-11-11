"""What an atlas holds once it has been expanded."""

from __future__ import annotations

import dataclasses as dc


@dc.dataclass(frozen=True, slots=True)
class ExpansionSummary:
    num_states: int
    num_actions: int
