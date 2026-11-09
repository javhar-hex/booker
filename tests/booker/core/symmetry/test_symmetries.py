from booker.core.symmetry.bliss_symmetry import BlissSymmetry
from booker.core.symmetry.symmetries import BLISS, SYMMETRIES, VF2
from booker.core.symmetry.vf2_symmetry import Vf2Symmetry


def test_the_names_are_those_that_command_lines_and_checkpoints_use() -> None:
    assert set(SYMMETRIES) == {"bliss", "vf2"}


def test_each_name_is_that_of_its_own_implementation() -> None:
    assert all(name == symmetry.name for name, symmetry in SYMMETRIES.items())
    assert (SYMMETRIES["bliss"], SYMMETRIES["vf2"]) == (BLISS, VF2)


def test_the_implementations_are_those_of_their_names() -> None:
    assert (type(BLISS), type(VF2)) == (BlissSymmetry, Vf2Symmetry)


def test_implementations_are_equal_by_value_and_never_to_one_another() -> None:
    assert BlissSymmetry() == BLISS
    assert Vf2Symmetry() == VF2
    assert SYMMETRIES["bliss"] != SYMMETRIES["vf2"]
