from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


def test_ranges_say_where_they_start_and_stop() -> None:
    assert str(StateIdRange()) == "[start, end)"
    assert str(StateIdRange.of(start=3, stop=9)) == "[3, 9)"


def test_a_range_is_unbounded_unless_it_is_told_otherwise() -> None:
    assert (StateIdRange().start, StateIdRange().stop) == (None, None)


def test_a_range_of_numbers_is_a_range_of_state_ids() -> None:
    assert StateIdRange.of(start=3, stop=9) == StateIdRange(
        start=StateId(value=3), stop=StateId(value=9)
    )
    assert StateIdRange.of() == StateIdRange()


def test_the_bounds_are_the_numbers_of_the_rows_where_there_are_any() -> None:
    bounded = StateIdRange.of(start=3, stop=9)

    assert (bounded.start_value, bounded.stop_value) == (3, 9)
    assert (StateIdRange().start_value, StateIdRange().stop_value) == (None, None)
