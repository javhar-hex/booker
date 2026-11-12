import pytest

from booker.atlas.packed_state import PackedState
from booker.core.model.state import State
from booker.verify.audit_failure import AuditFailure
from booker.verify.state_id import StateId
from booker.verify.state_row import StateRow

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
