from backend.stubs.verification_adapter import verify_credential
from backend.stubs.rotation_scheduler import schedule_recheck
import pytest

pytestmark = [pytest.mark.req("FR-6"), pytest.mark.req("NFR-6")]


def test_validity_stub_is_fail_closed():
    assert verify_credential("test", "EXAMPLE_FAKE_VALUE") == "unknown"


def test_rotation_stub_is_fail_closed():
    assert schedule_recheck("finding-EXAMPLE") == "unknown"
