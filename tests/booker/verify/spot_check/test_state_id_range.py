from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


def test_ranges_say_where_they_start_and_stop() -> None:
    assert str(StateIdRange()) == "[start, end)"
    assert str(StateIdRange(start=StateId(3), stop=StateId(9))) == "[3, 9)"
    assert str(StateIdRange(start=StateId(3))) == "[3, end)"
    assert str(StateIdRange(stop=StateId(9))) == "[start, 9)"


def test_a_range_is_unbounded_unless_it_is_told_otherwise() -> None:
    assert (StateIdRange().start, StateIdRange().stop) == (None, None)
