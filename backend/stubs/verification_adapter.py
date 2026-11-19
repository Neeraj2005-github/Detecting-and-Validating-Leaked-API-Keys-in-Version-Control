from typing import Protocol, Literal


ValidityResult = Literal["verified", "invalid", "unknown", "failed_to_check"]


class ValidityChecker(Protocol):
    def verify_credential(self, secret_type: str, secret_value: str) -> ValidityResult:
        """Semester VIII provider validity contract. Base stub never verifies or calls a network."""
        ...


class StubValidityChecker:
    def verify_credential(self, secret_type: str, secret_value: str) -> Literal["unknown"]:
        return "unknown"


def verify_credential(secret_type: str, secret_value: str) -> Literal["unknown"]:
    return StubValidityChecker().verify_credential(secret_type, secret_value)
