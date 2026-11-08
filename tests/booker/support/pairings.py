from booker.core.model.pairing import Pairing
from booker.core.model.team import Team


def pairing_of_indices(index_lhs: int, index_rhs: int) -> Pairing:
    return Pairing.of(Team(index=index_lhs), Team(index=index_rhs))
