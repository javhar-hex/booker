"""
The graph BLISS is handed: what it is coloured by, the relabelling that canonicalizes it,
and the generators of the symmetries that it finds.
"""

from javhar_util.immutables import ZSet, ZVec

from booker.core.model.pairing import Pairing
from booker.core.model.record import Record
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.bliss_graph import SCHEDULED_COLOUR, BlissGraph
from booker.core.symmetry.invariant import team_colour
from booker.core.symmetry.relabelling import Relabelling

ONE_ONE = Record(wins=1, losses=1)
WON = Record(wins=1, losses=0)
LOST = Record(wins=0, losses=1)
FRESH = Record.fresh()


def _pairing(a: int, b: int) -> Pairing:
    return Pairing.of(Team(index=a), Team(index=b))


def _schedule(
    records: list[Record],
    met: tuple[tuple[int, int], ...] = (),
    booked: tuple[tuple[int, int], ...] = (),
) -> Schedule:
    state = State(records=ZVec(records), met=ZSet(_pairing(a, b) for a, b in met))
    return Schedule(state=state, pairings=ZSet(_pairing(a, b) for a, b in booked))


def test_scheduled_pairings_are_a_colour_that_no_team_has() -> None:
    colours = {
        team_colour(Record(wins=wins, losses=losses))
        for wins in range(7)
        for losses in range(2)
    }

    assert len(colours) == 14
    assert max(colours) < SCHEDULED_COLOUR


def test_the_canonical_relabelling_is_a_permutation_of_the_teams() -> None:
    schedule = _schedule([ONE_ONE, WON, LOST, ONE_ONE], met=((0, 1), (2, 3)))

    relabelling = BlissGraph(schedule=schedule).canonical_relabelling

    assert len(relabelling) == schedule.state.size
    assert {relabelling.team(Team(index=i)).index for i in range(4)} == {0, 1, 2, 3}


def test_relabelled_schedules_are_relabelled_to_the_same_schedule() -> None:
    schedule = _schedule(
        [ONE_ONE, WON, LOST, ONE_ONE], met=((0, 1), (2, 3)), booked=((0, 3),)
    )
    shuffled = Relabelling.of([2, 0, 3, 1]).schedule(schedule)

    first = BlissGraph(schedule=schedule).canonical_relabelling.schedule(schedule)
    second = BlissGraph(schedule=shuffled).canonical_relabelling.schedule(shuffled)

    assert shuffled != schedule
    assert first == second


def test_the_generators_leave_the_schedule_as_it_was() -> None:
    schedule = _schedule([FRESH] * 4 + [WON, LOST], met=((4, 5),))

    generators = BlissGraph(schedule=schedule).automorphism_generators

    assert len(generators) > 0
    assert all(generator.schedule(schedule) == schedule for generator in generators)


def test_a_booked_pairing_leaves_only_the_symmetries_that_keep_it() -> None:
    schedule = _schedule([FRESH] * 4, booked=((0, 1),))

    generators = BlissGraph(schedule=schedule).automorphism_generators

    assert all(generator.schedule(schedule) == schedule for generator in generators)
    assert all(
        {generator.team(Team(index=0)).index, generator.team(Team(index=1)).index}
        == {0, 1}
        for generator in generators
    )


def test_a_schedule_without_symmetry_has_no_generators() -> None:
    schedule = _schedule([FRESH, WON, LOST, ONE_ONE])

    assert len(BlissGraph(schedule=schedule).automorphism_generators) == 0


def test_what_is_worked_out_is_worked_out_once() -> None:
    graph = BlissGraph(schedule=_schedule([FRESH] * 3))

    assert graph.canonical_relabelling is graph.canonical_relabelling
    assert graph.automorphism_generators is graph.automorphism_generators
