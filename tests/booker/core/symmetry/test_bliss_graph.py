"""
The graph BLISS is handed: what it is coloured by, the relabelling that canonicalizes it,
and the generators of the symmetries that it finds.
"""

from javhar_util.immutables import ZSet, ZVec
from support.pairings import pairing_of_indices

from booker.core.model.record import Record
from booker.core.model.schedule import Schedule
from booker.core.model.state import State
from booker.core.model.team import Team
from booker.core.symmetry.bliss_graph import SCHEDULED_COLOUR, BlissGraph, team_colour
from booker.core.symmetry.relabelling import Relabelling

RECORD_1_1 = Record(wins=1, losses=1)
RECORD_1_0 = Record(wins=1, losses=0)
RECORD_0_1 = Record(wins=0, losses=1)
RECORD_0_0 = Record.fresh()


def _schedule(
    records: list[Record],
    past_pairings: tuple[tuple[int, int], ...] = (),
    booked: tuple[tuple[int, int], ...] = (),
) -> Schedule:
    state = State(
        records=ZVec(records),
        past_pairings=ZSet(
            pairing_of_indices(index_lhs, index_rhs)
            for index_lhs, index_rhs in past_pairings
        ),
    )
    return Schedule(
        state=state,
        pairings=ZSet(
            pairing_of_indices(index_lhs, index_rhs) for index_lhs, index_rhs in booked
        ),
    )


def test_every_live_record_has_a_colour_of_its_own() -> None:
    records = [
        Record(wins=wins, losses=losses) for wins in range(7) for losses in range(2)
    ]

    assert len({team_colour(record) for record in records}) == len(records)


def test_scheduled_pairings_are_a_colour_that_no_team_has() -> None:
    colours = {
        team_colour(Record(wins=wins, losses=losses))
        for wins in range(7)
        for losses in range(2)
    }

    assert len(colours) == 14
    assert max(colours) < SCHEDULED_COLOUR


def test_the_canonical_relabelling_is_a_permutation_of_the_teams() -> None:
    schedule = _schedule(
        [RECORD_1_1, RECORD_1_0, RECORD_0_1, RECORD_1_1], past_pairings=((0, 1), (2, 3))
    )

    relabelling = BlissGraph(schedule=schedule).canonical_relabelling

    assert len(relabelling) == schedule.state.size
    assert {relabelling.team(Team(index=idx)).index for idx in range(4)} == {0, 1, 2, 3}


def test_relabelled_schedules_are_relabelled_to_the_same_schedule() -> None:
    schedule = _schedule(
        [RECORD_1_1, RECORD_1_0, RECORD_0_1, RECORD_1_1],
        past_pairings=((0, 1), (2, 3)),
        booked=((0, 3),),
    )
    shuffled = Relabelling.of([2, 0, 3, 1]).schedule(schedule)

    first = BlissGraph(schedule=schedule).canonical_relabelling.schedule(schedule)
    second = BlissGraph(schedule=shuffled).canonical_relabelling.schedule(shuffled)

    assert shuffled != schedule
    assert first == second


def test_the_generators_leave_the_schedule_as_it_was() -> None:
    schedule = _schedule(
        [RECORD_0_0] * 4 + [RECORD_1_0, RECORD_0_1], past_pairings=((4, 5),)
    )

    generators = BlissGraph(schedule=schedule).automorphism_generators

    assert len(generators) > 0
    assert all(generator.schedule(schedule) == schedule for generator in generators)


def test_a_booked_pairing_leaves_only_the_symmetries_that_keep_it() -> None:
    schedule = _schedule([RECORD_0_0] * 4, booked=((0, 1),))

    generators = BlissGraph(schedule=schedule).automorphism_generators

    assert all(generator.schedule(schedule) == schedule for generator in generators)
    assert all(
        {generator.team(Team(index=0)).index, generator.team(Team(index=1)).index}
        == {0, 1}
        for generator in generators
    )


def test_a_schedule_without_symmetry_has_no_generators() -> None:
    schedule = _schedule([RECORD_0_0, RECORD_1_0, RECORD_0_1, RECORD_1_1])

    assert len(BlissGraph(schedule=schedule).automorphism_generators) == 0


def test_what_is_worked_out_is_worked_out_once() -> None:
    graph = BlissGraph(schedule=_schedule([RECORD_0_0] * 3))

    assert graph.canonical_relabelling is graph.canonical_relabelling
    assert graph.automorphism_generators is graph.automorphism_generators


def test_a_relabelled_schedule_is_isomorphic_to_the_original() -> None:
    schedule = _schedule(
        [RECORD_1_1, RECORD_1_0, RECORD_0_1, RECORD_1_1],
        past_pairings=((0, 1), (2, 3)),
        booked=((0, 3),),
    )
    shuffled = Relabelling.of([2, 0, 3, 1]).schedule(schedule)

    assert shuffled != schedule
    assert BlissGraph(schedule=shuffled).is_isomorphic_to(BlissGraph(schedule=schedule))


def test_schedules_of_different_sizes_are_not_isomorphic() -> None:
    small = BlissGraph(schedule=_schedule([RECORD_0_0] * 2))
    large = BlissGraph(schedule=_schedule([RECORD_0_0] * 3))

    assert not small.is_isomorphic_to(large)
    assert not large.is_isomorphic_to(small)


def test_records_and_booked_pairings_tell_schedules_apart() -> None:
    records = [RECORD_0_0, RECORD_0_0, RECORD_1_0, RECORD_1_0]
    schedule = BlissGraph(schedule=_schedule(records, booked=((0, 1),)))

    assert not schedule.is_isomorphic_to(
        BlissGraph(schedule=_schedule(records, booked=((0, 2),)))
    )
    assert not schedule.is_isomorphic_to(BlissGraph(schedule=_schedule(records)))
