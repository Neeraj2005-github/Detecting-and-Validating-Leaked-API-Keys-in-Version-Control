# Evaluation Methodology

## Detection benchmark

[`backend/services/benchmark_engine.py`](../backend/services/benchmark_engine.py)
uses the same generated history fixture and oracle for Regex + Entropy, a
Gitleaks/native-or-emulator baseline, a detect-secrets baseline, and the O2
engine. Predictions are compared with oracle sets for six true positives and
four decoys.

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 * precision * recall / (precision + recall)
```

The recorded O2 artifact reports TP=6, FP=0, FN=0, precision=1.0, recall=1.0,
and F1=1.0 for that synthetic run. The separate RQ1 held-out 14-feature
XGBoost row reports precision 0.75, recall 1.0, and F1 0.8571428571428571.
These are different evaluation scopes.

## Feature ablation

[`backend/ml/xgboost_rigour.py`](../backend/ml/xgboost_rigour.py) evaluates
four feature groups on a frozen repository-group split:

1. Entropy.
2. Lexical statistics.
3. Lexical plus context/path features.
4. Full 14-feature vector.

The current checked-in ablation artifact records perfect metrics for each
configuration; it should not be described as evidence of a measured
step-by-step FPR reduction unless a corresponding artifact contains those
different FPR values.

## Prioritization

[`backend/ml/shap_risk_scorer.py`](../backend/ml/shap_risk_scorer.py) computes
TreeSHAP contributions and uses `sklearn.metrics.ndcg_score`. The RQ2 artifact
records composite-risk NDCG@10 of `0.959548213570596` and Precision@5 of `0.8`.
Relevance reflects active HEAD, branch/tag, historical, and decoy priority.

## Rotation

[`backend/services/rotation_state_machine.py`](../backend/services/rotation_state_machine.py)
measures monotonic execution time from detection acceptance to verified
inactive state in an in-memory SQLite database. The aggregate artifact reports
six successful rotations out of six and mean MTTR `1.2566499999999998 ms`.
This is sandbox execution time, not real provider revocation latency.

## Important limitations

- Fixtures are synthetic and small.
- Optional native tools can change baseline provenance.
- Model-only and complete-engine metrics must be labeled separately.
- Historical detection does not prove provider validity or revocation.
- Results are reproducible evidence for this repository, not a production SLA.
