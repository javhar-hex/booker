from booker.verify.audit.audit_progress import AuditProgress
from booker.verify.spot_check.pairing_count import PairingCount
from booker.verify.spot_check.state_id import StateId
from booker.verify.spot_check.state_id_range import StateIdRange


def test_a_whole_audit_starts_with_no_next_id() -> None:
    assert AuditProgress.start(StateIdRange()) == AuditProgress(
        next_state_id=None, num_checked_states=0, cml_pairing_count=PairingCount.none()
    )


def test_a_ranged_audit_starts_at_its_range() -> None:
    assert AuditProgress.start(StateIdRange(start=StateId(7))).next_state_id == StateId(
        value=7
    )


def test_progress_counts_what_each_state_brought() -> None:
    progress = AuditProgress.start(StateIdRange()).after(
        StateId(value=4), PairingCount(orbits=3, pairings=5)
    )

    assert progress == AuditProgress(
        next_state_id=StateId(value=5),
        num_checked_states=1,
        cml_pairing_count=PairingCount(orbits=3, pairings=5),
    )
    assert progress.after(
        StateId(value=9), PairingCount(orbits=1, pairings=1)
    ) == AuditProgress(
        next_state_id=StateId(value=10),
        num_checked_states=2,
        cml_pairing_count=PairingCount(orbits=4, pairings=6),
    )
