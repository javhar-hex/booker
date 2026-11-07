from collections.abc import Callable
from pathlib import Path

import pytest

from booker.atlas.atlas import Atlas
from booker.core.model.pairing import Pairing
from booker.core.model.state import State


def test_the_canonicalization_backend_cannot_change(path: Path) -> None:
    with Atlas.open(path) as atlas:
        writer = atlas.expansion_writer()
        writer.use_backend("bliss")
        writer.use_backend("bliss")

        with pytest.raises(ValueError, match="Cannot resume bliss atlas using vf2"):
            writer.use_backend("vf2")


def test_the_root_is_recorded_once(
    path: Path, final_pair: Callable[[bool], State], champion_state: State
) -> None:
    with Atlas.open(path) as atlas:
        writer = atlas.expansion_writer()
        first = writer.add_state(final_pair(False))
        second = writer.add_state(champion_state)
        writer.record_root(first)
        writer.record_root(second)

        row = atlas.connection.execute(
            "SELECT value FROM meta WHERE key='root_id'"
        ).fetchone()

    assert int(row[0]) == first.value


def test_an_action_is_stored_with_its_children(
    path: Path,
    final_pair: Callable[[bool], State],
    champion_state: State,
    pairing: Pairing,
) -> None:
    with Atlas.open(path) as atlas:
        writer = atlas.expansion_writer()
        parent = writer.add_state(final_pair(False))
        champion = writer.add_state(champion_state)
        writer.add_action(parent, pairing, False, 1, champion, champion)

        assert atlas.num_actions() == 1
