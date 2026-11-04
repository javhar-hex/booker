"""A position together with the identity under which an atlas stores it."""

from __future__ import annotations

import dataclasses as dc

from booker.atlas.state_id import StateId
from booker.core.model.state import State


@dc.dataclass(frozen=True, slots=True)
class StoredState:
    "A position, and the id that the atlas gave it."

    id: StateId
    state: State
