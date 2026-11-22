from backend.services.exposure_lifecycle import calculate_exposure_risk


def compute_risk_score(finding: dict) -> int:
    """Compute the explainable exposure-risk score for a finding."""
    return calculate_exposure_risk(finding)[0]
