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

LB_SURVIVOR_RECORD = Record(wins=4, losses=1)
"""
Two teams emerge from the lower bracket (LB) at this record, and the one team that
emerges unbeaten from the upper bracket then meets both of them.
"""


def legal_pairings(state: State) -> ZSet[Pairing]:
    """
    Teams of equal record may meet, except that two teams at `LB_SURVIVOR_RECORD` may
    not while any team is unbeaten. Once exactly one team is unbeaten, the upper bracket
    has produced its winner, who may meet only a team at `LB_SURVIVOR_RECORD`. Nothing else
    is legal; a leaf state has no pairings at all.
    """
    num_unbeaten = sum(record.is_unbeaten for record in state.records)
    return ZSet(
        Pairing.of(team_lo, team_hi)
        for team_lo, team_hi in itertools.combinations(state.teams, 2)
        if _may_meet(state.record(team_lo), state.record(team_hi), num_unbeaten)
    )


def _may_meet(record_lhs: Record, record_rhs: Record, num_unbeaten: int) -> bool:
    if record_lhs == record_rhs:
        return record_lhs != LB_SURVIVOR_RECORD or num_unbeaten == 0
    else:
        return num_unbeaten == 1 and (
            (record_lhs.is_unbeaten and record_rhs == LB_SURVIVOR_RECORD)
            or (record_rhs.is_unbeaten and record_lhs == LB_SURVIVOR_RECORD)
        )
