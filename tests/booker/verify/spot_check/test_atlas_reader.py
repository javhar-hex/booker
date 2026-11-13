from pathlib import Path

from booker.verify.spot_check.atlas_reader import AtlasReader
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


def test_the_ids_from_a_start_up_to_but_not_including_a_stop(endgame: Path) -> None:
    with AtlasReader.open(endgame) as reader:
        every_id = list(reader.state_ids(StateIdRange()))

        assert len(every_id) == 29
        assert (
            list(reader.state_ids(StateIdRange(start=every_id[2], stop=every_id[5])))
            == every_id[2:5]
        )


def test_without_a_stop_the_ids_go_on_to_the_last(endgame: Path) -> None:
    with AtlasReader.open(endgame) as reader:
        every_id = list(reader.state_ids(StateIdRange()))

        assert list(reader.state_ids(StateIdRange(start=every_id[-3]))) == every_id[-3:]


def test_without_a_start_the_ids_begin_with_the_first(endgame: Path) -> None:
    with AtlasReader.open(endgame) as reader:
        every_id = list(reader.state_ids(StateIdRange()))

        assert list(reader.state_ids(StateIdRange(stop=every_id[3]))) == every_id[:3]


def test_there_are_no_ids_in_an_empty_range(endgame: Path) -> None:
    with AtlasReader.open(endgame) as reader:
        assert (
            list(reader.state_ids(StateIdRange(start=StateId(5), stop=StateId(5)))) == []
        )
