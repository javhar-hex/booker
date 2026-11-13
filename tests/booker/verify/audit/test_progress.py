from booker.verify.audit.progress import Progress
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


def test_a_whole_audit_starts_with_no_next_id() -> None:
    assert Progress.start(StateIdRange()) == Progress(
        next_id=None, states=0, counted=PairingCount.none()
    )


def test_a_ranged_audit_starts_at_its_range() -> None:
    assert Progress.start(StateIdRange(start=StateId(7))).next_id == StateId(value=7)


def test_progress_counts_what_each_state_brought() -> None:
    progress = Progress.start(StateIdRange()).after(
        StateId(value=4), PairingCount(orbits=3, pairings=5)
    )

    assert progress == Progress(
        next_id=StateId(value=5), states=1, counted=PairingCount(orbits=3, pairings=5)
    )
    assert progress.after(
        StateId(value=9), PairingCount(orbits=1, pairings=1)
    ) == Progress(
        next_id=StateId(value=10), states=2, counted=PairingCount(orbits=4, pairings=6)
    )
