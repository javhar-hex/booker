import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.verify.isomorphism import (
    IGRAPH,
    NETWORKX,
    ColouredGraph,
    Mode,
    are_isomorphic,
)

ONE_ONE = Record(wins=1, losses=1)
ZERO_ONE = Record(wins=0, losses=1)


def _pairing(a: int, b: int) -> Pairing:
    return Pairing.of(Team(index=a), Team(index=b))


def _graph(colours: list[int], *edges: tuple[int, int]) -> ColouredGraph:
    return ColouredGraph(
        colours=ZVec(colours), edges=ZSet(_pairing(a, b) for a, b in edges)
    )


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_relabelled_graphs_are_isomorphic(mode: Mode) -> None:
    path = _graph([0, 0, 0, 0], (0, 1), (1, 2), (2, 3))
    relabelled = _graph([0, 0, 0, 0], (0, 2), (0, 3), (1, 3))

    assert are_isomorphic(path, relabelled, mode)


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_a_path_is_not_a_star(mode: Mode) -> None:
    path = _graph([0, 0, 0, 0], (0, 1), (1, 2), (2, 3))
    star = _graph([0, 0, 0, 0], (0, 1), (0, 2), (0, 3))

    assert not are_isomorphic(path, star, mode)


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_two_triangles_are_not_a_six_cycle(mode: Mode) -> None:
    triangles = _graph([0] * 6, (0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5))
    cycle = _graph([0] * 6, (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5))

    assert not are_isomorphic(triangles, cycle, mode)


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_colours_must_match(mode: Mode) -> None:
    at_the_end = _graph([1, 0, 0], (0, 1), (1, 2))
    in_the_middle = _graph([0, 1, 0], (0, 1), (1, 2))

    assert not are_isomorphic(at_the_end, in_the_middle, mode)
    assert are_isomorphic(at_the_end, _graph([0, 0, 1], (0, 1), (1, 2)), mode)


@pytest.mark.parametrize("mode", [IGRAPH, NETWORKX])
def test_graphs_of_different_sizes_are_not_isomorphic(mode: Mode) -> None:
    assert not are_isomorphic(_graph([0, 0]), _graph([0, 0, 0]), mode)
    assert not are_isomorphic(_graph([0, 0], (0, 1)), _graph([0, 0]), mode)


def test_a_state_is_coloured_by_its_records() -> None:
    state = State(records=ZVec([ONE_ONE, ZERO_ONE]), met=ZSet([_pairing(0, 1)]))

    graph = ColouredGraph.of(state)

    assert list(graph.colours) == [3, 1]
    assert graph.edges == state.met


def test_marking_a_pairing_sets_its_teams_apart() -> None:
    state = State(records=ZVec([ONE_ONE] * 3), met=ZSet([]))

    marked = ColouredGraph.marked(state, _pairing(0, 2))

    assert list(marked.colours) == [7, 6, 7]
