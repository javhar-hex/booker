from booker.verify.audit.id_range import IdRange
from booker.verify.audit.progress import BEFORE_ANY_ID, Progress
from booker.verify.spot_check.state_id import StateId


def test_a_whole_audit_starts_before_every_id() -> None:
    assert Progress.start(IdRange()) == Progress(
        next_id=BEFORE_ANY_ID, states=0, actions=0, pairings=0
    )


def test_a_ranged_audit_starts_at_its_range() -> None:
    assert Progress.start(IdRange(start=7)).next_id == 7


def test_progress_counts_what_each_state_brought() -> None:
    progress = Progress.start(IdRange()).after(StateId(value=4), actions=3, pairings=5)

    assert progress == Progress(next_id=5, states=1, actions=3, pairings=5)
    assert progress.after(StateId(value=9), 1, 1) == Progress(
        next_id=10, states=2, actions=4, pairings=6
    )
