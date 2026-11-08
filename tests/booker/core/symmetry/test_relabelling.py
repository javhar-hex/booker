import pytest
from javhar_util.immutables import ZMap, ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.relabelling import Relabelling

TEAM_A, TEAM_B, TEAM_C = (Team(index=idx) for idx in range(3))
ROTATION = Relabelling.of([1, 2, 0])
UNBEATEN = Record(wins=2, losses=0)
ONE_LOSS = Record(wins=1, losses=1)
STATE = State(
    records=ZVec([UNBEATEN, ONE_LOSS, ONE_LOSS]),
    past_pairings=ZSet([Pairing.of(TEAM_A, TEAM_B)]),
)


def test_rejects_two_teams_with_one_image() -> None:
    with pytest.raises(ValueError, match="not a permutation"):
        Relabelling.of([0, 0, 2])


def test_rejects_teams_beyond_the_state() -> None:
    with pytest.raises(ValueError, match="not a permutation"):
        Relabelling(
            images=ZMap({TEAM_A: TEAM_B, TEAM_B: Team(index=5), Team(index=5): TEAM_A})
        )


def test_maps_teams_and_pairings() -> None:
    assert ROTATION.team(TEAM_A) == TEAM_B
    assert ROTATION.pairing(Pairing.of(TEAM_B, TEAM_C)) == Pairing.of(TEAM_A, TEAM_C)


def test_moves_each_record_with_its_team() -> None:
    relabelled = ROTATION.state(STATE)

    assert relabelled.record(TEAM_B) == UNBEATEN
    assert relabelled.past_pairings == ZSet([Pairing.of(TEAM_B, TEAM_C)])


def test_relabels_a_schedule_consistently() -> None:
    schedule = Schedule(state=STATE, pairings=ZSet([Pairing.of(TEAM_B, TEAM_C)]))

    relabelled = ROTATION.schedule(schedule)

    assert relabelled.pairings == ZSet([Pairing.of(TEAM_A, TEAM_C)])
    assert relabelled.state == ROTATION.state(STATE)


def test_identity_changes_nothing() -> None:
    assert Relabelling.of([0, 1, 2]).state(STATE) == STATE


def test_rejects_a_state_of_another_size() -> None:
    with pytest.raises(ValueError, match="relabels 2 teams"):
        Relabelling.of([1, 0]).state(STATE)
