"""
The game's rules, written again here from the description of the tournament rather than
shared with the generator: which pairings are legal, and what a match does.
"""

from __future__ import annotations

import dataclasses as dc
import itertools

from javhar_util.immutables import ZSet, ZVec

from booker.verify.position import Pair, Position, Standing
from booker.verify.spec import ELIMINATION_LOSSES

LOWER_BRACKET_SURVIVOR = Standing(wins=4, losses=1)


@dc.dataclass(frozen=True, slots=True)
class Played:
    "The position after a match, and whether it was a repeat of an earlier one."

    position: Position
    is_rematch: bool


def legal_pairs(position: Position) -> ZSet[Pair]:
    num_unbeaten = position.num_unbeaten
    return ZSet(
        Pair(low=i, high=j)
        for i, j in itertools.combinations(range(position.size), 2)
        if _may_meet(position.standings[i], position.standings[j], num_unbeaten)
    )


def play(position: Position, winner: int, loser: int) -> Played:
    pair = Pair(low=min(winner, loser), high=max(winner, loser))
    standings = list(position.standings)
    standings[winner] = Standing(
        wins=standings[winner].wins + 1, losses=standings[winner].losses
    )
    standings[loser] = Standing(
        wins=standings[loser].wins, losses=standings[loser].losses + 1
    )
    survivors = [i for i, s in enumerate(standings) if s.losses < ELIMINATION_LOSSES]
    renumbered = {old: new for new, old in enumerate(survivors)}
    met = (
        Pair(low=renumbered[m.low], high=renumbered[m.high])
        for m in position.meetings | ZSet([pair])
        if m.low in renumbered and m.high in renumbered
    )
    return Played(
        position=Position(
            standings=ZVec(standings[i] for i in survivors), meetings=ZSet(met)
        ),
        is_rematch=pair in position.meetings,
    )


def _may_meet(x: Standing, y: Standing, num_unbeaten: int) -> bool:
    if x == y:
        return x != LOWER_BRACKET_SURVIVOR or num_unbeaten == 0
    return num_unbeaten == 1 and (
        (x.is_unbeaten and y == LOWER_BRACKET_SURVIVOR)
        or (y.is_unbeaten and x == LOWER_BRACKET_SURVIVOR)
    )
