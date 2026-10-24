"""Orbits of legal pairings under a state's automorphisms, on hand-countable states.

Random states are covered by the verifier, which checks every orbit in the atlas.
"""

from __future__ import annotations

from booker.state import State, pairing_classes, start


def test_all_first_round_pairings_are_one_class() -> None:
    assert pairing_classes(start()) == [((0, 1), 120)]


def test_two_disjoint_matches_leave_three_classes() -> None:
    fresh = ((0, 0),) * 12
    played = ((1, 0), (0, 1), (1, 0), (0, 1))
    state = State(fresh + played, ((12, 13), (14, 15)))
    assert pairing_classes(state) == [((0, 1), 66), ((12, 14), 1), ((13, 15), 1)]


def test_rematch_is_its_own_class() -> None:
    state = State(((1, 1),) * 4, ((0, 1),))
    assert pairing_classes(state) == [((0, 1), 1), ((0, 2), 4), ((2, 3), 1)]


def test_terminal_state_has_no_classes() -> None:
    assert pairing_classes(State(((6, 0),), ())) == []
