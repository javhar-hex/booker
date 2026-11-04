"""
The implementations of `Symmetry`, by name: the one place that knows them all, so that
a name on a command line, or in a checkpoint file, can be turned into one.
"""

from __future__ import annotations

import enum

from booker.core.symmetry.bliss_symmetry import BlissSymmetry
from booker.core.symmetry.symmetry import Symmetry
from booker.core.symmetry.vf2_symmetry import Vf2Symmetry


class SymmetryKind(enum.Enum):
    "The values are the names that command lines and checkpoint files use."

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
