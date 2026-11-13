import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.atlas.packed_state import PackedState
from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_row import StateRow

STATE_ID = StateId(value=7)


def test_decodes_the_position_of_a_row() -> None:
    row = (PackedState.of(State.start()).data, 0, 16, None, 1)

    assert StateRow.of(STATE_ID, row) == StateRow(
        state=State.start(), depth=0, num_teams=16, value=None, is_expanded=True
    )


def test_an_expanded_flag_of_zero_is_not_expanded() -> None:
    row = (PackedState.of(State.start()).data, 0, 16, 3, 0)

    state_row = StateRow.of(STATE_ID, row)

    assert (state_row.is_expanded, state_row.value) == (False, 3)


def test_a_position_that_cannot_be_decoded_fails_the_audit_by_its_id() -> None:
    with pytest.raises(AuditFailure, match="state 7: invalid position"):
        StateRow.of(STATE_ID, (b"", 0, 16, None, 1))


def test_the_columns_are_those_that_of_takes_in_order() -> None:
    assert StateRow.COLUMNS.split(",") == ["key", "depth", "active", "value", "expanded"]


def _row(state: State, depth: int, num_teams: int, is_expanded: bool = True) -> StateRow:
    return StateRow(
        state=state,
        depth=depth,
        num_teams=num_teams,
        value=None,
        is_expanded=is_expanded,
    )


CHAMPION = Record(wins=6, losses=0)
LAST_TEAM_STANDING = State(records=ZVec([CHAMPION]), past_pairings=ZSet([]))
CHAMPION_AND_ONE_MORE = State(
    records=ZVec([CHAMPION, Record(wins=3, losses=1)]), past_pairings=ZSet([])
)


@pytest.mark.parametrize(
    "state_row",
    [
        _row(State.start(), depth=0, num_teams=16),
        _row(LAST_TEAM_STANDING, depth=30, num_teams=1),
    ],
)
def test_a_row_that_agrees_with_its_position_is_consistent(state_row: StateRow) -> None:
    state_row.require_consistent(STATE_ID)


@pytest.mark.parametrize(
    ("state_row", "complaint"),
    [
        (_row(State.start(), depth=0, num_teams=15), "team count or depth"),
        (
            _row(State.start(), depth=MAX_MATCHES + 1, num_teams=16),
            "team count or depth",
        ),
        (
            _row(State.start(), depth=1, num_teams=16),
            "depth 1, but its teams have played 0",
        ),
        (
            _row(LAST_TEAM_STANDING, depth=30, num_teams=1, is_expanded=False),
            "bad decided",
        ),
        (
            _row(
                State(records=ZVec([Record(wins=5, losses=0)]), past_pairings=ZSet([])),
                30,
                1,
            ),
            "bad decided",
        ),
        (_row(CHAMPION_AND_ONE_MORE, depth=29, num_teams=2), "a champion, with teams"),
    ],
)
def test_a_row_that_disagrees_with_its_position_fails_the_audit(
    state_row: StateRow, complaint: str
) -> None:
    with pytest.raises(AuditFailure, match=f"state 7: .*{complaint}"):
        state_row.require_consistent(STATE_ID)
