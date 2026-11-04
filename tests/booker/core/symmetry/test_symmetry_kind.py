import pytest

from booker.core.symmetry.bliss_symmetry import BlissSymmetry
from booker.core.symmetry.symmetry_kind import BLISS, VF2, SymmetryKind
from booker.core.symmetry.vf2_symmetry import Vf2Symmetry


def test_the_names_are_those_that_command_lines_and_checkpoints_use() -> None:
    assert {kind.value for kind in SymmetryKind} == {"bliss", "vf2"}
    assert (SymmetryKind("bliss"), SymmetryKind("vf2")) == (BLISS, VF2)


def test_each_kind_is_its_own_implementation() -> None:
    assert type(BLISS.symmetry) is BlissSymmetry
    assert type(VF2.symmetry) is Vf2Symmetry


def test_an_unknown_name_is_not_a_kind() -> None:
    with pytest.raises(ValueError):
        SymmetryKind("networkx")
