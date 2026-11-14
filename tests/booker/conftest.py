import random
from collections.abc import Callable, Iterator

import pytest

from booker.core.model.outcome import Outcome
from booker.core.model.state import State
from booker.core.model.successor import successor
from booker.game.rules import legal_pairings


def _play_game(rng: random.Random) -> Iterator[State]:
    "Every state of one random game, from the start to the leaf state."
    state = State.start()
    yield state
    while not state.is_leaf:
        pairing = rng.choice(sorted(legal_pairings(state)))
        winner = rng.choice((pairing.lhs, pairing.rhs))
        state = successor(state, Outcome.single(pairing, winner))
        yield state


@pytest.fixture
def play_game() -> Callable[[random.Random], Iterator[State]]:
    return _play_game
