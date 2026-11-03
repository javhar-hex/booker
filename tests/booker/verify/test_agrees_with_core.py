"""
The verifier shares nothing with the generator, on purpose. These tests are what keep
the two honest: wherever both have an opinion, they must hold the same one.
"""

import ast
import random
from collections.abc import Callable, Iterator
from pathlib import Path

from javhar_util.immutables import ZSet, ZVec

import booker.verify
from booker.atlas.codec import PackedState
from booker.atlas.schema import META, SCHEMA_VERSION
from booker.core.model.invariants import (
    CHAMPION_WINS,
    ELIMINATION_LOSSES,
    MAX_MATCHES,
    NUM_PARTICIPANTS,
)
from booker.core.model.outcome import Outcome
from booker.core.model.state import State
from booker.core.model.successor import successor
from booker.generate.rules import LOWER_BRACKET_SURVIVOR, legal_pairings
from booker.verify import spec
from booker.verify.position import Pair, Position, Standing
from booker.verify.rules import LOWER_BRACKET_SURVIVOR as VERIFIER_SURVIVOR
from booker.verify.rules import legal_pairs, play


def _position(state: State) -> Position:
    return Position(
        standings=ZVec(Standing(wins=r.wins, losses=r.losses) for r in state.records),
        meetings=ZSet(Pair(low=p.low.index, high=p.high.index) for p in state.met),
    )


def _states(
    play_game: Callable[[random.Random], Iterator[State]],
) -> list[State]:
    rng = random.Random(0)
    return [state for _ in range(15) for state in play_game(rng)]


def test_the_verifier_takes_the_game_to_be_what_core_does() -> None:
    assert spec.NUM_TEAMS == NUM_PARTICIPANTS
    assert spec.ELIMINATION_LOSSES == ELIMINATION_LOSSES
    assert spec.CHAMPION_WINS == CHAMPION_WINS
    assert spec.MAX_MATCHES == MAX_MATCHES
    assert (VERIFIER_SURVIVOR.wins, VERIFIER_SURVIVOR.losses) == (
        LOWER_BRACKET_SURVIVOR.wins,
        LOWER_BRACKET_SURVIVOR.losses,
    )


def test_the_verifier_takes_the_atlas_to_be_what_the_generator_writes() -> None:
    assert spec.SCHEMA_VERSION == SCHEMA_VERSION
    assert spec.GAME == META["game"]


def test_keys_parse_to_the_positions_they_were_packed_from(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    for state in _states(play_game):
        assert Position.parse(PackedState.of(state).data) == _position(state)


def test_the_same_pairings_are_legal(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    for state in _states(play_game):
        expected = ZSet(
            Pair(low=p.low.index, high=p.high.index) for p in legal_pairings(state)
        )
        assert legal_pairs(_position(state)) == expected


def test_a_match_leads_to_the_same_position_at_the_same_cost(
    play_game: Callable[[random.Random], Iterator[State]],
) -> None:
    for state in _states(play_game):
        for pairing in legal_pairings(state):
            for winner, loser in (
                (pairing.low, pairing.high),
                (pairing.high, pairing.low),
            ):
                played = play(_position(state), winner.index, loser.index)

                assert played.position == _position(
                    successor(state, Outcome.single(pairing, winner))
                )
                assert played.is_rematch == state.has_met(pairing)


def test_the_verifier_imports_nothing_from_the_rest_of_booker() -> None:
    package = Path(booker.verify.__file__).parent
    imported = {
        node.module
        for source in package.glob("*.py")
        for node in ast.walk(ast.parse(source.read_text()))
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for source in package.glob("*.py")
        for node in ast.walk(ast.parse(source.read_text()))
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert "booker.verify.position" in imported
    assert {name for name in imported if name.startswith("booker")} <= {
        name for name in imported if name.startswith("booker.verify")
    }
