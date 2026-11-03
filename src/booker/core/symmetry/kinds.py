"""The implementations of `Symmetry`, by name."""

from __future__ import annotations

import enum

from booker.core.symmetry.bliss import BlissSymmetry
from booker.core.symmetry.interface import Symmetry
from booker.core.symmetry.vf2 import Vf2Symmetry


class SymmetryKind(enum.Enum):
    BLISS = "bliss"
    VF2 = "vf2"

    @property
    def symmetry(self) -> Symmetry:
        if self is SymmetryKind.BLISS:
            return BlissSymmetry()
        else:
            return Vf2Symmetry()


BLISS = SymmetryKind.BLISS
VF2 = SymmetryKind.VF2
