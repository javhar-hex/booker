"""The checks on one position, its actions, and the values it and they are given."""

from __future__ import annotations

import dataclasses as dc

from javhar_util.immutables import ZMap, ZSet, ZVec

from booker.core.model.invariants import CHAMPION_WINS, MAX_MATCHES
from booker.core.model.outcome import Outcome
from booker.core.model.successor import successor
from booker.game.rules import legal_pairings
from booker.verify.database import ActionRow, Database, StateId, StoredState
from booker.verify.failure import AuditFailure
from booker.verify.isomorphism import ColouredGraph, Mode, are_isomorphic
from booker.verify.orbits import check_orbits


@dc.dataclass(frozen=True, slots=True)
class Tally:
    actions: int
    pairings: int


@dc.dataclass(frozen=True, slots=True)
class StateCheck:
    """
    Checks a position as the atlas stores it, and when it is solved the Bellman
    equations too: a Collider position is worth the larger of its two children, and a
    Scheduler position the least, over its actions, of what the action costs and is
    worth.
    """

    db: Database
    mode: Mode
    is_solved: bool

    def run(self, state_id: StateId) -> Tally:
        stored = self.db.stored(state_id)
        _check_standings(state_id, stored)
        rows = self.db.actions(state_id)
        self._check_pairings(state_id, stored, rows)
        for row in rows:
            self._check_children(state_id, stored, row)
        if self.is_solved:
            self._check_values(state_id, stored, rows)
        return Tally(actions=len(rows), pairings=sum(row.class_size for row in rows))

    def _check_pairings(
        self, state_id: StateId, stored: StoredState, rows: ZVec[ActionRow]
    ) -> None:
        pairings = ZSet(row.pairing for row in rows)
        if len(pairings) != len(rows):
            raise AuditFailure(f"state {state_id.value}: a pairing is stored twice")
        if not stored.is_expanded:
            if rows:
                raise AuditFailure(f"state {state_id.value}: unexpanded, with actions")
            return
        if illegal := pairings - legal_pairings(stored.state):
            raise AuditFailure(f"state {state_id.value}: illegal pairings {illegal}")
        check_orbits(
            stored.state,
            ZMap({row.pairing: row.class_size for row in rows}),
            self.mode,
        )
        if (not rows) != stored.state.is_decided:
            raise AuditFailure(
                f"state {state_id.value}: a dead end, or a decided state with moves"
            )

    def _check_children(
        self, state_id: StateId, stored: StoredState, row: ActionRow
    ) -> None:
        pairing = row.pairing
        if int(stored.state.has_met(pairing)) != row.repeat_cost:
            raise AuditFailure(
                f"state {state_id.value}, pairing {pairing}: "
                f"wrong repeat cost {row.repeat_cost}"
            )
        for winner, child_id in (
            (pairing.low, row.low_wins),
            (pairing.high, row.high_wins),
        ):
            where = f"state {state_id.value}, pairing {pairing}, winner {winner.index}"
            expected = successor(stored.state, Outcome.single(pairing, winner))
            child = self.db.stored(child_id).state
            if not are_isomorphic(
                ColouredGraph.of(expected), ColouredGraph.of(child), self.mode
            ):
                raise AuditFailure(f"{where}: leads to the wrong state {child_id.value}")
            if child.matches_played != stored.depth + 1:
                raise AuditFailure(f"{where}: the child is not one match deeper")

    def _check_values(
        self, state_id: StateId, stored: StoredState, rows: ZVec[ActionRow]
    ) -> None:
        if stored.value is None:
            raise AuditFailure(f"state {state_id.value}: unsolved")
        if stored.state.is_decided and stored.value != 0:
            raise AuditFailure(f"state {state_id.value}: a decided state is worth 0")
        options = [self._option(state_id, row) for row in rows]
        if options and stored.value != min(options):
            raise AuditFailure(
                f"state {state_id.value}: value {stored.value}, but its best action "
                f"is worth {min(options)}"
            )

    def _option(self, state_id: StateId, row: ActionRow) -> int:
        "What the Scheduler gets by choosing this action: its cost plus its value."
        low = self.db.stored(row.low_wins).value
        high = self.db.stored(row.high_wins).value
        if low is None or high is None:
            raise AuditFailure(f"state {state_id.value}: a child is unsolved")
        if row.value != max(low, high):
            raise AuditFailure(
                f"state {state_id.value}, pairing {row.pairing}: Collider value "
                f"{row.value}, but the children are worth {low} and {high}"
            )
        return row.repeat_cost + row.value


def _check_standings(state_id: StateId, stored: StoredState) -> None:
    state = stored.state
    if stored.num_teams != state.size or not 0 <= stored.depth <= MAX_MATCHES:
        raise AuditFailure(f"state {state_id.value}: inconsistent team count or depth")
    if stored.depth != state.matches_played:
        raise AuditFailure(
            f"state {state_id.value}: depth {stored.depth}, but its teams have "
            f"played {state.matches_played} matches"
        )
    if state.is_decided:
        if state.records[0].wins != CHAMPION_WINS or not stored.is_expanded:
            raise AuditFailure(f"state {state_id.value}: a bad decided state")
    elif any(record.wins >= CHAMPION_WINS for record in state.records):
        raise AuditFailure(
            f"state {state_id.value}: a champion, with teams still playing"
        )
