from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.relabelling import Relabelling
from booker.generate.state_canonicalizer import StateCanonicalizer

RECORD_1_1 = Record(wins=1, losses=1)
RECORD_1_0 = Record(wins=1, losses=0)
RECORD_0_1 = Record(wins=0, losses=1)


def _met(*pairs: tuple[int, int]) -> ZSet[Pairing]:
    return ZSet(
        Pairing.of(Team(index=index_lhs), Team(index=index_rhs))
        for index_lhs, index_rhs in pairs
    )


def _state(records: list[Record], past_pairings: ZSet[Pairing]) -> State:
    return State(records=ZVec(records), past_pairings=past_pairings)


def _six_teams(*edges: tuple[int, int]) -> State:
    return _state([RECORD_1_1] * 6, _met(*edges))


TWO_TRIANGLES = _six_teams((0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5))
SIX_CYCLE = _six_teams((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5))


def test_the_first_state_of_its_kind_is_its_own_representative() -> None:
    assert StateCanonicalizer([])(TWO_TRIANGLES) == TWO_TRIANGLES


def test_a_relabelled_state_maps_to_the_first_one_seen() -> None:
    canonicalizer = StateCanonicalizer([])
    relabelled = Relabelling.of([2, 0, 4, 1, 5, 3]).state(SIX_CYCLE)

    assert canonicalizer(SIX_CYCLE) == SIX_CYCLE
    assert relabelled != SIX_CYCLE
    assert canonicalizer(relabelled) == SIX_CYCLE


def test_states_alike_in_every_signature_but_not_isomorphic_stay_apart() -> None:
    canonicalizer = StateCanonicalizer([])

    assert canonicalizer(TWO_TRIANGLES) == TWO_TRIANGLES
    assert canonicalizer(SIX_CYCLE) == SIX_CYCLE


def test_records_travel_with_their_teams() -> None:
    canonicalizer = StateCanonicalizer([])
    winner_first = _state([RECORD_1_0, RECORD_0_1], _met((0, 1)))
    winner_second = _state([RECORD_0_1, RECORD_1_0], _met((0, 1)))

    assert canonicalizer(winner_first) == winner_first
    assert canonicalizer(winner_second) == winner_first


def test_states_with_different_records_stay_apart() -> None:
    canonicalizer = StateCanonicalizer([])
    mixed = _state([RECORD_1_1, RECORD_0_1], _met((0, 1)))
    alike = _state([RECORD_1_1, RECORD_1_1], _met((0, 1)))

    assert canonicalizer(mixed) == mixed
    assert canonicalizer(alike) == alike


def test_states_of_different_sizes_stay_apart() -> None:
    canonicalizer = StateCanonicalizer([])
    small = _state([RECORD_1_1] * 2, _met())

    assert canonicalizer(small) == small
    assert canonicalizer(_state([RECORD_1_1] * 3, _met())) != small


def test_known_states_are_the_representatives() -> None:
    relabelled = Relabelling.of([2, 0, 4, 1, 5, 3]).state(SIX_CYCLE)
    canonicalizer = StateCanonicalizer([SIX_CYCLE])

    assert canonicalizer(relabelled) == SIX_CYCLE
