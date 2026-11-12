from booker.core.model.pairing import Pairing
from booker.core.model.team import Team
from booker.verify.action_row import ActionRow
from booker.verify.state_id import StateId


def test_builds_the_pairing_and_the_children_of_a_row() -> None:
    row = (2, 5, 1, 40, 41, 12, None)

    assert ActionRow.of(row) == ActionRow(
        pairing=Pairing.of(Team(index=2), Team(index=5)),
        repeat_cost=1,
        lhs_wins=StateId(value=40),
        rhs_wins=StateId(value=41),
        class_size=12,
        value=None,
    )


def test_a_solved_row_has_its_value() -> None:
    assert ActionRow.of((0, 1, 0, 2, 3, 1, 4)).value == 4


def test_the_columns_are_those_that_of_takes_in_order() -> None:
    assert ActionRow.COLUMNS.split(",") == [
        "lhs",
        "rhs",
        "repeat_cost",
        "lhs_wins",
        "rhs_wins",
        "class_size",
        "value",
    ]
