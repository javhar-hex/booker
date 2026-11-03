import pytest
from javhar_util.immutables import ZMap, ZSet, ZVec

from booker.verify.failure import AuditFailure
from booker.verify.isomorphism import IGRAPH, NETWORKX, Mode
from booker.verify.orbits import are_equivalent, check_orbits
from booker.verify.position import Pair, Position, Standing

ONE_ONE = Standing(wins=1, losses=1)


def _pair(a: int, b: int) -> Pair:
    return Pair(low=a, high=b)


def _position(count: int, *met: tuple[int, int]) -> Position:
    return Position(
        standings=ZVec([ONE_ONE] * count), meetings=ZSet(_pair(a, b) for a, b in met)
    )


REMATCH_POSITION = _position(4, (0, 1))
CORRECT_ORBITS = ZMap({_pair(0, 1): 1, _pair(0, 2): 4, _pair(2, 3): 1})


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_pairings_of_alike_teams_are_equivalent(mode: Mode) -> None:
    assert are_equivalent(REMATCH_POSITION, _pair(0, 2), _pair(1, 3), mode)
    assert are_equivalent(REMATCH_POSITION, _pair(0, 2), _pair(0, 2), mode)


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_a_rematch_is_equivalent_to_no_other_pairing(mode: Mode) -> None:
    assert not are_equivalent(REMATCH_POSITION, _pair(0, 1), _pair(2, 3), mode)
    assert not are_equivalent(REMATCH_POSITION, _pair(0, 2), _pair(2, 3), mode)


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_accepts_one_representative_per_orbit_with_its_size(mode: Mode) -> None:
    check_orbits(REMATCH_POSITION, CORRECT_ORBITS, mode)


def test_rejects_a_wrong_class_size() -> None:
    wrong = ZMap({_pair(0, 1): 1, _pair(0, 2): 5, _pair(2, 3): 1})

    with pytest.raises(AuditFailure, match="orbit sizes"):
        check_orbits(REMATCH_POSITION, wrong, NETWORKX)


def test_rejects_two_representatives_of_one_orbit() -> None:
    twice = ZMap({_pair(0, 1): 1, _pair(0, 2): 2, _pair(1, 3): 2, _pair(2, 3): 1})

    with pytest.raises(AuditFailure, match="orbit representatives"):
        check_orbits(REMATCH_POSITION, twice, NETWORKX)


def test_rejects_an_orbit_with_no_representative() -> None:
    missing = ZMap({_pair(0, 1): 1, _pair(0, 2): 4})

    with pytest.raises(AuditFailure, match="orbit representatives"):
        check_orbits(REMATCH_POSITION, missing, NETWORKX)
