import itertools
import random
from collections import deque
from collections.abc import Callable, Iterator

from javhar_util.immutables import ZSet, ZVec

from booker.core.model.invariants import NUM_PARTICIPANTS
from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.game.rules import LOWER_BRACKET_SURVIVOR, legal_pairings

TEAM_A, TEAM_B, TEAM_C = (Team(index=idx) for idx in range(3))
UNBEATEN = Record(wins=2, losses=0)
OTHER_UNBEATEN = Record(wins=3, losses=0)
ONE_LOSS = Record(wins=3, losses=1)
CHAMPION_UNBEATEN = Record(wins=6, losses=0)
CHAMPION_ONE_LOSS = Record(wins=6, losses=1)


def _state(*records: Record) -> State:
    return State(records=ZVec(records), past_pairings=ZSet([]))


def _pairings(*pairs: tuple[Team, Team]) -> ZSet[Pairing]:
    return ZSet(Pairing.of(team_lhs, team_rhs) for team_lhs, team_rhs in pairs)


def test_everyone_may_meet_everyone_at_the_start() -> None:
    teams = State.start().teams

    assert legal_pairings(State.start()) == _pairings(*itertools.combinations(teams, 2))
    assert len(legal_pairings(State.start())) == NUM_PARTICIPANTS * 15 // 2


def test_teams_of_different_records_may_not_meet() -> None:
    assert legal_pairings(_state(ONE_LOSS, Record(wins=2, losses=1))) == ZSet([])


def test_teams_of_equal_record_may_meet() -> None:
    state = _state(ONE_LOSS, ONE_LOSS, UNBEATEN, OTHER_UNBEATEN)

    assert legal_pairings(state) == _pairings((TEAM_A, TEAM_B))


def test_lower_bracket_survivors_may_not_meet_while_a_team_is_unbeaten() -> None:
    survivor = LOWER_BRACKET_SURVIVOR

    assert legal_pairings(_state(survivor, survivor, UNBEATEN)) == _pairings(
        (TEAM_A, TEAM_C), (TEAM_B, TEAM_C)
    )
    assert legal_pairings(_state(survivor, survivor, UNBEATEN, OTHER_UNBEATEN)) == (
        ZSet([])
    )


def test_lower_bracket_survivors_may_meet_once_no_team_is_unbeaten() -> None:
    survivor = LOWER_BRACKET_SURVIVOR

    assert legal_pairings(_state(survivor, survivor)) == _pairings((TEAM_A, TEAM_B))


def test_sole_unbeaten_team_may_meet_only_a_lower_bracket_survivor() -> None:
    state = _state(ONE_LOSS, LOWER_BRACKET_SURVIVOR, UNBEATEN)

    assert legal_pairings(state) == _pairings((TEAM_B, TEAM_C))


def test_one_of_two_unbeaten_teams_may_not_meet_a_lower_bracket_survivor() -> None:
    state = _state(LOWER_BRACKET_SURVIVOR, UNBEATEN, OTHER_UNBEATEN)

    assert legal_pairings(state) == ZSet([])


def test_decided_state_has_no_pairings() -> None:
    assert legal_pairings(_state(CHAMPION_ONE_LOSS)) == ZSet([])


def test_every_game_ends_in_one_of_the_two_possible_decided_states(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    rng = random.Random(0)

    endings = {
        (final.records[0], final.matches_played)
        for final in (deque(play_game(rng), maxlen=1)[0] for _ in range(200))
    }

    assert endings <= {
        (CHAMPION_UNBEATEN, 30),
        (CHAMPION_ONE_LOSS, 31),
    }
