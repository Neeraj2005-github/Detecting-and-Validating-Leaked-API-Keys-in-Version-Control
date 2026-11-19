from typing import Protocol, Literal


RotationResult = Literal["unknown", "scheduled", "verified-revoked"]


class RotationVerifier(Protocol):
    def verify_rotation(self, finding_id: str) -> RotationResult:
        ...


class StubRotationVerifier:
    def verify_rotation(self, finding_id: str) -> Literal["unknown"]:
        return "unknown"


def schedule_recheck(finding_id: str) -> Literal["unknown"]:
    return StubRotationVerifier().verify_rotation(finding_id)
