"""Whether the stored pairings are exactly one per orbit of the legal pairings."""

from __future__ import annotations

from javhar_util.immutables import ZMap

from booker.verify.failure import AuditFailure
from booker.verify.isomorphism import ColouredGraph, Mode, are_isomorphic
from booker.verify.position import Pair, Position
from booker.verify.rules import legal_pairs


def check_orbits(position: Position, stored: ZMap[Pair, int], mode: Mode) -> None:
    """
    Each legal pairing is equivalent, under the position's automorphisms, to exactly one
    stored pairing, whose class size is the number of legal pairings equivalent to it.
    """
    hits = dict.fromkeys(stored, 0)
    for pair in legal_pairs(position):
        matches = [
            representative
            for representative in stored
            if are_equivalent(position, pair, representative, mode)
        ]
        if len(matches) != 1:
            raise AuditFailure(
                f"orbit representatives: {pair} is equivalent to {matches} in {position}"
            )
        hits[matches[0]] += 1
    if ZMap(hits) != stored:
        raise AuditFailure(f"orbit sizes: found {hits}, stored {dict(stored.items())}")


def are_equivalent(position: Position, x: Pair, y: Pair, mode: Mode) -> bool:
    "Is there an automorphism of the position that maps pair `x` onto pair `y`?"
    if (x in position.meetings) != (y in position.meetings):
        return False
    return are_isomorphic(
        ColouredGraph.marked(position, x), ColouredGraph.marked(position, y), mode
    )
