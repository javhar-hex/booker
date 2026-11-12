from __future__ import annotations

from booker.verify.spot_check.state_id import StateId


class AuditFailure(Exception):
    "The atlas is not what its generator and solver claim it is."

    @classmethod
    def of(cls, state_id: StateId, detail: str) -> AuditFailure:
        "What is wrong with the position `state_id`."
        return cls(f"state {state_id.value}: {detail}")
