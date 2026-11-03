import pytest
from javhar_util.immutables import ZSet, ZVec

from booker.verify.isomorphism import (
    IGRAPH,
    NETWORKX,
    ColouredGraph,
    Mode,
    are_isomorphic,
)
from booker.verify.position import Pair, Position, Standing

ONE_ONE = Standing(wins=1, losses=1)
ZERO_ONE = Standing(wins=0, losses=1)


def _graph(colours: list[int], *edges: tuple[int, int]) -> ColouredGraph:
    return ColouredGraph(
        colours=ZVec(colours), edges=ZSet(Pair(low=a, high=b) for a, b in edges)
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


def test_a_position_is_coloured_by_its_standings() -> None:
    position = Position(
        standings=ZVec([ONE_ONE, ZERO_ONE]), meetings=ZSet([Pair(low=0, high=1)])
    )

    graph = ColouredGraph.of(position)

    assert list(graph.colours) == [ONE_ONE.colour, ZERO_ONE.colour]
    assert graph.edges == position.meetings


def test_marking_a_pair_sets_its_teams_apart() -> None:
    position = Position(standings=ZVec([ONE_ONE] * 3), meetings=ZSet([]))

    marked = ColouredGraph.marked(position, Pair(low=0, high=2))

    assert list(marked.colours) == [
        2 * ONE_ONE.colour + 1,
        2 * ONE_ONE.colour,
        2 * ONE_ONE.colour + 1,
    ]
