"""
The Scheduler's legal pairings in the unrestricted game: no round barriers, any legal
pairing may be booked at any time. The rules are exactly those that keep the
(16, 2, 6) tournament's champion at 6 wins and everyone else eliminated at 2 losses.
"""

from __future__ import annotations

import itertools

from javhar_util.immutables import ZSet

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State

LOWER_BRACKET_SURVIVOR = Record(wins=4, losses=1)
"""
Two teams emerge from the lower bracket at this record, and the one team that emerges
unbeaten from the upper bracket then meets both of them.
"""


def legal_pairings(state: State) -> ZSet[Pairing]:
    """
    Teams of equal record may meet, except that two `LOWER_BRACKET_SURVIVOR` teams may
    not while any team is unbeaten. Once exactly one team is unbeaten, the upper bracket
    has produced its winner, who may meet only a `LOWER_BRACKET_SURVIVOR`. Nothing else
    is legal; a decided state has no pairings at all.
    """
    num_unbeaten = sum(record.is_unbeaten for record in state.records)
    return ZSet(
        Pairing.of(a, b)
        for a, b in itertools.combinations(state.teams, 2)
        if _may_meet(state.record(a), state.record(b), num_unbeaten)
    )


def _may_meet(x: Record, y: Record, num_unbeaten: int) -> bool:
    return _equals_may_meet(x, y, num_unbeaten) or _sole_unbeaten_may_meet(
        x, y, num_unbeaten
    )


def _equals_may_meet(x: Record, y: Record, num_unbeaten: int) -> bool:
    return x == y and (x != LOWER_BRACKET_SURVIVOR or num_unbeaten == 0)


def _sole_unbeaten_may_meet(x: Record, y: Record, num_unbeaten: int) -> bool:
    return num_unbeaten == 1 and (
        (x.is_unbeaten and y == LOWER_BRACKET_SURVIVOR)
        or (y.is_unbeaten and x == LOWER_BRACKET_SURVIVOR)
    )
