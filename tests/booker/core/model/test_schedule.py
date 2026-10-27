import pytest
from javhar_util.immutables import ZSet

from booker.core.model.invariants import NUM_PARTICIPANTS
from booker.core.model.pairing import Pairing
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.model.team import Team


def test_empty_schedule_has_no_pairings() -> None:
    schedule = Schedule.empty(State.start())

    assert schedule.state == State.start()
    assert len(schedule.pairings) == 0


def test_rejects_scheduling_a_team_not_in_the_state() -> None:
    outsider = Pairing.of(Team(index=0), Team(index=NUM_PARTICIPANTS))

    with pytest.raises(ValueError, match="not one of"):
        Schedule(state=State.start(), pairings=ZSet([outsider]))
