from javhar_util.immutables import ZSet, ZVec

from booker.core.model.record import Record
from booker.core.model.state import State
from support.pairings import pairing_of_indices


def state_of_indices(records: list[Record], *index_pairs: tuple[int, int]) -> State:
    "A state of these records, in which the teams of each pair of indices have met."
    return State(
        records=ZVec(records),
        past_pairings=ZSet(
            pairing_of_indices(index_lhs, index_rhs)
            for index_lhs, index_rhs in index_pairs
        ),
    )
