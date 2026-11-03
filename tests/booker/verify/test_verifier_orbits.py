import pytest
from javhar_util.immutables import ZMap, ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.verify.failure import AuditFailure
from booker.verify.isomorphism import IGRAPH, NETWORKX, Mode
from booker.verify.orbits import are_equivalent, check_orbits

ONE_ONE = Record(wins=1, losses=1)


def _pairing(a: int, b: int) -> Pairing:
    return Pairing.of(Team(index=a), Team(index=b))


REMATCH_STATE = State(records=ZVec([ONE_ONE] * 4), met=ZSet([_pairing(0, 1)]))
CORRECT_ORBITS = ZMap({_pairing(0, 1): 1, _pairing(0, 2): 4, _pairing(2, 3): 1})


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_pairings_of_alike_teams_are_equivalent(mode: Mode) -> None:
    assert are_equivalent(REMATCH_STATE, _pairing(0, 2), _pairing(1, 3), mode)
    assert are_equivalent(REMATCH_STATE, _pairing(0, 2), _pairing(0, 2), mode)


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_a_rematch_is_equivalent_to_no_other_pairing(mode: Mode) -> None:
    assert not are_equivalent(REMATCH_STATE, _pairing(0, 1), _pairing(2, 3), mode)
    assert not are_equivalent(REMATCH_STATE, _pairing(0, 2), _pairing(2, 3), mode)


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_accepts_one_representative_per_orbit_with_its_size(mode: Mode) -> None:
    check_orbits(REMATCH_STATE, CORRECT_ORBITS, mode)


def test_rejects_a_wrong_class_size() -> None:
    wrong = ZMap({_pairing(0, 1): 1, _pairing(0, 2): 5, _pairing(2, 3): 1})

    with pytest.raises(AuditFailure, match="orbit sizes"):
        check_orbits(REMATCH_STATE, wrong, NETWORKX)


def test_rejects_two_representatives_of_one_orbit() -> None:
    twice = ZMap(
        {_pairing(0, 1): 1, _pairing(0, 2): 2, _pairing(1, 3): 2, _pairing(2, 3): 1}
    )

    with pytest.raises(AuditFailure, match="orbit representatives"):
        check_orbits(REMATCH_STATE, twice, NETWORKX)


def test_rejects_an_orbit_with_no_representative() -> None:
    missing = ZMap({_pairing(0, 1): 1, _pairing(0, 2): 4})

    with pytest.raises(AuditFailure, match="orbit representatives"):
        check_orbits(REMATCH_STATE, missing, NETWORKX)
