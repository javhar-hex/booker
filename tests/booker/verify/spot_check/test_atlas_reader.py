from pathlib import Path

from booker.verify.spot_check.atlas_reader import AtlasReader


def test_the_ids_from_a_start_up_to_but_not_including_a_stop(endgame: Path) -> None:
    with AtlasReader.open(str(endgame)) as reader:
        every_id = list(reader.state_ids(0, None))

        assert len(every_id) == 29
        assert (
            list(reader.state_ids(every_id[2].value, every_id[5].value)) == every_id[2:5]
        )


def test_without_a_stop_the_ids_go_on_to_the_last(endgame: Path) -> None:
    with AtlasReader.open(str(endgame)) as reader:
        every_id = list(reader.state_ids(0, None))

        assert list(reader.state_ids(every_id[-3].value, None)) == every_id[-3:]


def test_there_are_no_ids_in_an_empty_range(endgame: Path) -> None:
    with AtlasReader.open(str(endgame)) as reader:
        assert list(reader.state_ids(5, 5)) == []
