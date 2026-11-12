"""The checks on one position, its actions, and the values it and they are given."""

from __future__ import annotations

import dataclasses as dc

from javhar_util.immutables import ZSet, ZVec

from booker.core.model.invariants import CHAMPION_WINS, MAX_MATCHES
from booker.core.model.outcome import Outcome
from booker.core.model.pairing import Pairing
from booker.core.model.state import State
from booker.core.model.successor import successor
from booker.core.symmetry.orbits import PairingOrbits
from booker.core.symmetry.state_symmetry import StateSymmetry, signature
from booker.game.rules import legal_pairings
from booker.verify.audit_failure import AuditFailure
from booker.verify.database import ActionRow, Database, StateId, StoredState


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
    worth. Children and orbits are checked cheaply, and with a `symmetry` thoroughly.
    """

    db: Database
    symmetry: StateSymmetry | None
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
        legal = legal_pairings(stored.state)
        if illegal := pairings - legal:
            raise AuditFailure(f"state {state_id.value}: illegal pairings {illegal}")
        if (size := sum(row.class_size for row in rows)) != len(legal):
            raise AuditFailure(
                f"state {state_id.value}: orbit sizes add up to {size}, "
                f"but {len(legal)} pairings are legal"
            )
        if (not rows) != stored.state.is_decided:
            raise AuditFailure(
                f"state {state_id.value}: a dead end, or a decided state with moves"
            )
        if self.symmetry is not None:
            _check_orbits(state_id, self.symmetry.orbits(stored.state, legal), rows)

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
            (pairing.lhs, row.lhs_wins),
            (pairing.rhs, row.rhs_wins),
        ):
            where = f"state {state_id.value}, pairing {pairing}, winner {winner.index}"
            expected = successor(stored.state, Outcome.single(pairing, winner))
            child = self.db.stored(child_id).state
            if child.matches_played != stored.depth + 1:
                raise AuditFailure(f"{where}: the child is not one match deeper")
            if not self._is_the_same_state(expected, child):
                raise AuditFailure(f"{where}: leads to the wrong state {child_id.value}")

    def _is_the_same_state(self, expected: State, stored: State) -> bool:
        if signature(expected) != signature(stored):
            return False
        return self.symmetry is None or self.symmetry.are_isomorphic(expected, stored)

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
        value_lhs = self.db.stored(row.lhs_wins).value
        value_rhs = self.db.stored(row.rhs_wins).value
        if value_lhs is None or value_rhs is None:
            raise AuditFailure(f"state {state_id.value}: a child is unsolved")
        if row.value != max(value_lhs, value_rhs):
            raise AuditFailure(
                f"state {state_id.value}, pairing {row.pairing}: Collider value "
                f"{row.value}, but the children are worth {value_lhs} and {value_rhs}"
            )
        return row.repeat_cost + row.value


def _check_orbits(
    state_id: StateId, orbits: PairingOrbits, rows: ZVec[ActionRow]
) -> None:
    "Each orbit has exactly one stored pairing, which carries the orbit's size."
    sizes = {row.pairing: row.class_size for row in rows}
    for orbit in orbits:
        representatives = [pairing for pairing in sizes if pairing in orbit.members]
        if len(representatives) != 1:
            raise AuditFailure(
                f"state {state_id.value}: orbit representatives: "
                f"{_names(representatives)} stored for the orbit of {_names(orbit.members)}"
            )
        if sizes[representatives[0]] != orbit.size:
            raise AuditFailure(
                f"state {state_id.value}: orbit sizes: {representatives[0]} is stored "
                f"as {sizes[representatives[0]]}, but its orbit has {orbit.size}"
            )


def _names(pairings: ZSet[Pairing] | list[Pairing]) -> list[tuple[int, int]]:
    return sorted((p.lhs.index, p.rhs.index) for p in pairings)


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
