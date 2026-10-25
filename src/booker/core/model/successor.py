from __future__ import annotations

from collections import Counter

from booker.core.model.outcome import Outcome
from booker.core.model.pairing import Pairing
from booker.core.model.state import State
from booker.core.model.team import Team
from util.dtypes.immutables.z_set import ZSet
from util.dtypes.immutables.z_vec import ZVec


def successor(state: State, outcome: Outcome) -> State:
    """
    The state after every match of `outcome`: records updated, the pairings added to
    who-has-met-whom, and eliminated teams dropped, the survivors renumbered in order.
    """
    _require_known_teams(state, outcome)
    wins = Counter(outcome.winner(pairing) for pairing in outcome.pairings)
    losses = Counter(outcome.loser(pairing) for pairing in outcome.pairings)
    records = [
        state.record(team).plus(wins=wins[team], losses=losses[team])
        for team in state.teams
    ]
    survivors = [team for team in state.teams if not records[team.index].is_eliminated]
    renumbered = {old: Team(index=new) for new, old in enumerate(survivors)}
    met = (
        Pairing.of(renumbered[p.low], renumbered[p.high])
        for p in state.met | outcome.pairings
        if p.low in renumbered and p.high in renumbered
    )
    return State(records=ZVec(records[t.index] for t in survivors), met=ZSet(met))


def _require_known_teams(state: State, outcome: Outcome) -> None:
    for pairing in outcome.pairings:
        state.require_known(pairing.high)
