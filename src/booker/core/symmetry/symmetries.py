"""
The implementations of `Symmetry`, by name: the one place that knows them all, so that
a name on a command line, or in a checkpoint file, can be turned into one.
"""

from __future__ import annotations

from javhar_util.immutables import ZMap

from booker.core.symmetry.bliss_symmetry import BlissSymmetry
from booker.core.symmetry.symmetry import Symmetry
from booker.core.symmetry.vf2_symmetry import Vf2Symmetry

BLISS = BlissSymmetry()
VF2 = Vf2Symmetry()

SYMMETRIES: ZMap[str, Symmetry] = ZMap(
    {symmetry.name: symmetry for symmetry in [BLISS, VF2]}
)
