"""The checks on one position, its actions, and the values it and they are given."""

from __future__ import annotations

import dataclasses as dc

from javhar_util.immutables import ZMap, ZSet, ZVec

from booker.verify.database import ActionRow, Database, StateId, StoredPosition
from booker.verify.failure import AuditFailure
from booker.verify.isomorphism import ColouredGraph, Mode, are_isomorphic
from booker.verify.orbits import check_orbits
from booker.verify.rules import legal_pairs, play
from booker.verify.spec import CHAMPION_WINS, MAX_MATCHES


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
        self, state_id: StateId, stored: StoredPosition, rows: ZVec[ActionRow]
    ) -> None:
        pairs = ZSet(row.pair for row in rows)
        if len(pairs) != len(rows):
            raise AuditFailure(f"state {state_id.value}: a pairing is stored twice")
        if not stored.is_expanded:
            if rows:
                raise AuditFailure(f"state {state_id.value}: unexpanded, with actions")
            return
        if illegal := pairs - legal_pairs(stored.position):
            raise AuditFailure(f"state {state_id.value}: illegal pairings {illegal}")
        check_orbits(
            stored.position, ZMap({row.pair: row.class_size for row in rows}), self.mode
        )
        if (not rows) != stored.position.is_decided:
            raise AuditFailure(
                f"state {state_id.value}: a dead end, or a decided state with moves"
            )

    def _check_children(
        self, state_id: StateId, stored: StoredPosition, row: ActionRow
    ) -> None:
        pair = row.pair
        for winner, loser, child_id in (
            (pair.low, pair.high, row.low_wins),
            (pair.high, pair.low, row.high_wins),
        ):
            played = play(stored.position, winner, loser)
            where = f"state {state_id.value}, pairing {pair}, winner {winner}"
            if int(played.is_rematch) != row.repeat_cost:
                raise AuditFailure(f"{where}: wrong repeat cost {row.repeat_cost}")
            child = self.db.stored(child_id).position
            if not are_isomorphic(
                ColouredGraph.of(played.position), ColouredGraph.of(child), self.mode
            ):
                raise AuditFailure(f"{where}: leads to the wrong state {child_id.value}")
            if child.depth != stored.depth + 1:
                raise AuditFailure(f"{where}: the child is not one match deeper")

    def _check_values(
        self, state_id: StateId, stored: StoredPosition, rows: ZVec[ActionRow]
    ) -> None:
        if stored.value is None:
            raise AuditFailure(f"state {state_id.value}: unsolved")
        if stored.position.is_decided and stored.value != 0:
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
                f"state {state_id.value}, pairing {row.pair}: Collider value "
                f"{row.value}, but the children are worth {low} and {high}"
            )
        return row.repeat_cost + row.value


def _check_standings(state_id: StateId, stored: StoredPosition) -> None:
    position = stored.position
    if stored.num_teams != position.size or not 0 <= stored.depth <= MAX_MATCHES:
        raise AuditFailure(f"state {state_id.value}: inconsistent team count or depth")
    if stored.depth != position.depth:
        raise AuditFailure(
            f"state {state_id.value}: depth {stored.depth}, but its teams have "
            f"played {position.depth} matches"
        )
    if position.is_decided:
        decided_properly = (
            position.standings[0].wins == CHAMPION_WINS and stored.is_expanded
        )
        if not decided_properly:
            raise AuditFailure(f"state {state_id.value}: a bad decided state")
    elif any(standing.wins >= CHAMPION_WINS for standing in position.standings):
        raise AuditFailure(
            f"state {state_id.value}: a champion, with teams still playing"
        )
    for meeting in position.meetings:
        both = (position.standings[meeting.low], position.standings[meeting.high])
        if all(standing.is_unbeaten for standing in both):
            raise AuditFailure(f"state {state_id.value}: unbeaten teams have met")
