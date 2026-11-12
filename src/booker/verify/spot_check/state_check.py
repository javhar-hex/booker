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
from booker.verify.spot_check.action_row import ActionRow
from booker.verify.spot_check.atlas_reader import AtlasReader
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_row import StateRow


@dc.dataclass(frozen=True, slots=True)
class StateCheck:
    """
    Checks a position as the atlas stores it and, when the atlas is solved, its
    game-theoretical value (GTV) too. The GTV of a Collider position is the larger of the
    GTVs of its two children. The GTV of a Scheduler position is the least, over its
    children, of the action's cost plus the GTV of the child. Children and orbits are
    checked cheaply, and with a `symmetry` thoroughly.
    """

    db: AtlasReader
    symmetry: StateSymmetry | None
    is_solved: bool

    def run(self, state_id: StateId) -> PairingCount:
        state_row = self.db.state_row(state_id)
        _check_standings(state_id, state_row)
        action_rows = self.db.action_rows(state_id)
        self._check_pairings(state_id, state_row, action_rows)
        for action_row in action_rows:
            self._check_children(state_id, state_row, action_row)
        if self.is_solved:
            self._check_values(state_id, state_row, action_rows)
        return PairingCount.of(action_rows)

    def _check_pairings(
        self,
        state_id: StateId,
        state_row: StateRow,
        action_rows: ZVec[ActionRow],
    ) -> None:
        pairings = ZSet(action_row.pairing for action_row in action_rows)
        if len(pairings) != len(action_rows):
            raise AuditFailure.of(state_id, "a pairing is stored twice")
        if not state_row.is_expanded:
            if action_rows:
                raise AuditFailure.of(state_id, "unexpanded, with actions")
            return
        legal = legal_pairings(state_row.state)
        if illegal := pairings - legal:
            raise AuditFailure.of(state_id, f"illegal pairings {illegal}")
        self._check_pairings_covered(state_id, state_row, action_rows, legal)

    def _check_pairings_covered(
        self,
        state_id: StateId,
        state_row: StateRow,
        action_rows: ZVec[ActionRow],
        legal: ZSet[Pairing],
    ) -> None:
        "The stored orbits account for every legal pairing, and are the symmetry's orbits."
        size = sum(action_row.class_size for action_row in action_rows)
        if size != len(legal):
            raise AuditFailure.of(
                state_id,
                f"orbit sizes add up to {size}, but {len(legal)} pairings are legal",
            )
        if (not action_rows) != state_row.state.is_decided:
            raise AuditFailure.of(state_id, "a dead end, or a decided state with moves")
        if self.symmetry is not None:
            _check_orbits(
                state_id, self.symmetry.orbits(state_row.state, legal), action_rows
            )

    def _check_children(
        self, state_id: StateId, state_row: StateRow, action_row: ActionRow
    ) -> None:
        pairing = action_row.pairing
        if int(state_row.state.has_met(pairing)) != action_row.repeat_cost:
            raise AuditFailure.of(
                state_id,
                f"pairing {pairing}: wrong repeat cost {action_row.repeat_cost}",
            )
        for winner, child_id in (
            (pairing.lhs, action_row.lhs_wins),
            (pairing.rhs, action_row.rhs_wins),
        ):
            where = f"pairing {pairing}, winner {winner.index}"
            expected = successor(state_row.state, Outcome.single(pairing, winner))
            child = self.db.state_row(child_id).state
            if child.matches_played != state_row.depth + 1:
                raise AuditFailure.of(
                    state_id, f"{where}: the child is not one match deeper"
                )
            if not self._is_the_same_state(expected, child):
                raise AuditFailure.of(
                    state_id, f"{where}: leads to the wrong state {child_id.value}"
                )

    def _is_the_same_state(self, expected: State, stored_state: State) -> bool:
        if signature(expected) != signature(stored_state):
            return False
        return self.symmetry is None or self.symmetry.are_isomorphic(
            expected, stored_state
        )

    def _check_values(
        self,
        state_id: StateId,
        state_row: StateRow,
        action_rows: ZVec[ActionRow],
    ) -> None:
        if state_row.value is None:
            raise AuditFailure.of(state_id, "unsolved")
        if state_row.state.is_decided and state_row.value != 0:
            raise AuditFailure.of(state_id, "a decided state is worth 0")
        options = [
            self._checked_option(state_id, action_row) for action_row in action_rows
        ]
        if options and state_row.value != min(options):
            raise AuditFailure.of(
                state_id,
                f"value {state_row.value}, but its best action is worth {min(options)}",
            )

    def _checked_option(self, state_id: StateId, action_row: ActionRow) -> int:
        """
        What the Scheduler gets by choosing this action: its cost plus its GTV, once the
        Collider's GTV is checked to be the larger of its children's.
        """
        value_lhs = self.db.state_row(action_row.lhs_wins).value
        value_rhs = self.db.state_row(action_row.rhs_wins).value
        if value_lhs is None or value_rhs is None:
            raise AuditFailure.of(state_id, "a child is unsolved")
        if action_row.value != max(value_lhs, value_rhs):
            raise AuditFailure.of(
                state_id,
                f"pairing {action_row.pairing}: Collider value {action_row.value}, "
                f"but the children are worth {value_lhs} and {value_rhs}",
            )
        return action_row.repeat_cost + action_row.value


def _check_orbits(
    state_id: StateId, orbits: PairingOrbits, action_rows: ZVec[ActionRow]
) -> None:
    "Each orbit has exactly one stored pairing, which carries the orbit's size."
    sizes = {action_row.pairing: action_row.class_size for action_row in action_rows}
    for orbit in orbits:
        representatives = [pairing for pairing in sizes if pairing in orbit.members]
        if len(representatives) != 1:
            raise AuditFailure.of(
                state_id,
                f"orbit representatives: {len(representatives)} stored for the orbit of "
                f"{min(orbit.members)} ({orbit.size} pairings): {representatives}",
            )
        if sizes[representatives[0]] != orbit.size:
            raise AuditFailure.of(
                state_id,
                f"orbit sizes: {representatives[0]} is stored "
                f"as {sizes[representatives[0]]}, but its orbit has {orbit.size}",
            )


def _check_standings(state_id: StateId, state_row: StateRow) -> None:
    state = state_row.state
    if state_row.num_teams != state.size or not 0 <= state_row.depth <= MAX_MATCHES:
        raise AuditFailure.of(state_id, "inconsistent team count or depth")
    if state_row.depth != state.matches_played:
        raise AuditFailure.of(
            state_id,
            f"depth {state_row.depth}, but its teams have "
            f"played {state.matches_played} matches",
        )
    if state.is_decided:
        if state.records[0].wins != CHAMPION_WINS or not state_row.is_expanded:
            raise AuditFailure.of(state_id, "a bad decided state")
    elif any(record.wins >= CHAMPION_WINS for record in state.records):
        raise AuditFailure.of(state_id, "a champion, with teams still playing")
