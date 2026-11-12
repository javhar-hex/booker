from booker.verify.spot_check.audit_failure import AuditFailure
from booker.verify.spot_check.state_id import StateId


def test_a_failure_of_a_position_says_which_position_and_what_is_wrong() -> None:
    failure = AuditFailure.of(StateId(value=7), "a pairing is stored twice")

    assert str(failure) == "state 7: a pairing is stored twice"


def test_a_failure_is_an_exception() -> None:
    assert isinstance(AuditFailure.of(StateId(value=1), "wrong"), Exception)
