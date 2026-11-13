from booker.verify.spot_check.state_id import StateId


def test_a_state_id_prints_as_its_number() -> None:
    assert str(StateId(value=42)) == "42"


def test_state_ids_are_ordered_by_their_numbers() -> None:
    assert StateId(value=2) < StateId(value=10)
