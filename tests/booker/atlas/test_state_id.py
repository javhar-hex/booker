import pytest

from booker.atlas.state_id import StateId


def test_state_ids_are_numbered_from_one() -> None:
    with pytest.raises(ValueError):
        StateId(value=0)


def test_state_ids_are_in_order_of_their_numbers() -> None:
    assert StateId(value=1) < StateId(value=2)
    assert sorted([StateId(value=3), StateId(value=1)]) == [
        StateId(value=1),
        StateId(value=3),
    ]
