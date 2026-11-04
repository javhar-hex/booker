from collections.abc import Callable
from pathlib import Path

import pytest

from booker.atlas.atlas import Atlas
from booker.atlas.atlas_transaction import AtlasTransaction
from booker.atlas.state_id import StateId
from booker.core.model.pairing import Pairing
from booker.core.model.state import State


def test_a_failed_transaction_writes_nothing(path: Path, champion_state: State) -> None:
    with Atlas.open(path) as atlas:
        with pytest.raises(RuntimeError), atlas.transaction() as tx:
            tx.add_state(champion_state)
            raise RuntimeError("interrupted")

        assert atlas.num_states() == 0


def test_the_canonicalization_backend_cannot_change(path: Path) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            tx.use_backend("bliss")
            tx.use_backend("bliss")
        with pytest.raises(ValueError), atlas.transaction() as tx:
            tx.use_backend("vf2")


def test_an_action_is_stored_with_its_children(
    path: Path,
    final_pair: Callable[[bool], State],
    champion_state: State,
    pairing: Pairing,
) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            parent = tx.add_state(final_pair(False))
            champion = tx.add_state(champion_state)
            tx.add_action(parent, pairing, False, 1, champion, champion)

        assert atlas.num_actions() == 1


def _writes(
    parent: StateId, pairing: Pairing
) -> dict[str, Callable[[AtlasTransaction], object]]:
    return {
        "use_backend": lambda tx: tx.use_backend("bliss"),
        "record_root": lambda tx: tx.record_root(parent),
        "mark_expanded": lambda tx: tx.mark_expanded(parent),
        "mark_decided_expanded": lambda tx: tx.mark_decided_expanded(),
        "add_action": lambda tx: tx.add_action(
            parent, pairing, False, 1, parent, parent
        ),
    }


@pytest.mark.parametrize(
    "name",
    [
        "use_backend",
        "record_root",
        "mark_expanded",
        "mark_decided_expanded",
        "add_action",
    ],
)
def test_a_transaction_that_is_over_refuses_every_write(
    path: Path, champion_state: State, pairing: Pairing, name: str
) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            stored = tx.add_state(champion_state)

        with pytest.raises(RuntimeError, match="over"):
            _writes(stored, pairing)[name](tx)


def test_a_transaction_that_is_over_cannot_add_a_state(
    path: Path, champion_state: State
) -> None:
    with Atlas.open(path) as atlas:
        with atlas.transaction() as tx:
            tx.add_state(champion_state)

        with pytest.raises(RuntimeError, match="over"):
            tx.add_state(champion_state)

        assert atlas.num_states() == 1


def test_a_transaction_that_failed_is_over_too(
    path: Path, champion_state: State
) -> None:
    with Atlas.open(path) as atlas:
        with pytest.raises(ValueError), atlas.transaction() as tx:
            raise ValueError("interrupted")

        with pytest.raises(RuntimeError, match="over"):
            tx.add_state(champion_state)

        assert atlas.num_states() == 0
