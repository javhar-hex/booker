import pytest

from booker.core.model.invariants import CHAMPION_WINS, ELIMINATION_LOSSES
from booker.core.model.record import Record


def test_fresh_record_has_played_nothing() -> None:
    record = Record.fresh()

    assert record.played == 0
    assert record.is_unbeaten
    assert not record.is_eliminated


def test_plus_adds_wins_and_losses() -> None:
    assert Record(wins=3, losses=1).plus(wins=2, losses=1) == Record(wins=5, losses=2)


def test_losing_every_life_eliminates() -> None:
    record = Record.fresh().plus(wins=0, losses=ELIMINATION_LOSSES)

    assert record.is_eliminated
    assert not record.is_unbeaten


def test_reads_as_wins_dash_losses() -> None:
    assert str(Record(wins=4, losses=1)) == "4-1"


@pytest.mark.parametrize(
    "wins, losses",
    [(-1, 0), (0, -1), (CHAMPION_WINS + 1, 0), (0, ELIMINATION_LOSSES + 1)],
)
def test_rejects_impossible_records(wins: int, losses: int) -> None:
    with pytest.raises(ValueError):
        Record(wins=wins, losses=losses)


def test_rejects_taking_back_results() -> None:
    with pytest.raises(ValueError, match="take back"):
        Record(wins=2, losses=1).plus(wins=-1, losses=0)


def test_eliminated_team_plays_no_more() -> None:
    with pytest.raises(ValueError, match="no more matches"):
        Record(wins=3, losses=ELIMINATION_LOSSES).plus(wins=1, losses=0)


def test_eliminated_team_may_be_left_unchanged() -> None:
    eliminated = Record(wins=3, losses=ELIMINATION_LOSSES)

    assert eliminated.plus(wins=0, losses=0) == eliminated
