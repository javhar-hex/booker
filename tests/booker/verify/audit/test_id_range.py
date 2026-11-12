from booker.verify.audit.id_range import IdRange


def test_ranges_say_where_they_start_and_stop() -> None:
    assert str(IdRange()) == "[start, end)"
    assert str(IdRange(start=3, stop=9)) == "[3, 9)"
