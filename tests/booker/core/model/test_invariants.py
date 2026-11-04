import random
from collections import deque
from collections.abc import Callable, Iterator

from booker.core.model.invariants import MAX_MATCHES
from booker.core.model.state import State


def test_no_game_is_longer_than_the_most_matches_it_can_take(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    rng = random.Random(0)

    lengths = {deque(play_game(rng), maxlen=1)[0].matches_played for _ in range(100)}

    assert max(lengths) == MAX_MATCHES
    assert MAX_MATCHES == 31
