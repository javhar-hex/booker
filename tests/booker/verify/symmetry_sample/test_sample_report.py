from booker.verify.symmetry_sample.sample_report import SampleReport


def test_a_report_says_how_much_was_asked() -> None:
    report = SampleReport(states=2500, orbit_questions=2500, isomorphism_questions=12345)

    assert str(report) == (
        "AGREE: 2,500 states, 2,500 orbit questions, 12,345 isomorphism questions"
    )
