"""What the sample of states found."""

from __future__ import annotations

import dataclasses as dc


@dc.dataclass(frozen=True, slots=True)
class SampleReport:
    states: int
    orbit_questions: int
    isomorphism_questions: int

    def __str__(self) -> str:
        return (
            f"AGREE: {self.states:,} states, {self.orbit_questions:,} orbit questions, "
            f"{self.isomorphism_questions:,} isomorphism questions"
        )
