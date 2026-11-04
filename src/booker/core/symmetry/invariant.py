"""What an isomorphism cannot change, as cheap necessary conditions."""

from __future__ import annotations

import dataclasses as dc
from collections import Counter

from javhar_util.immutables import ZVec

from booker.core.model.invariants import ELIMINATION_LOSSES
from booker.core.model.record import Record
from booker.core.model.state import State


@dc.dataclass(frozen=True, slots=True, order=True)
class TeamSignature:
    "What an isomorphism cannot change about one team."

    wins: int
    losses: int
    degree: int


def team_colour(record: Record) -> int:
    "The colour of a team in a graph of a state: distinct for every live record."
    return record.wins * ELIMINATION_LOSSES + record.losses


def signature(state: State) -> ZVec[TeamSignature]:
    """
    Each team's record and number of previous opponents, sorted. States that are
    isomorphic have equal signatures; the converse does not hold, so equal signatures
    are not an answer, but different ones are.
    """
    degree = Counter(
        team for pairing in state.met for team in (pairing.low, pairing.high)
    )
    return ZVec(
        sorted(
            TeamSignature(wins=record.wins, losses=record.losses, degree=degree[team])
            for team, record in zip(state.teams, state.records)
        )
    )
