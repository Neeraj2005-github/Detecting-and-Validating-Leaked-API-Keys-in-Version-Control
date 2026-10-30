# Secret History Detector (SHD) – Review Summary

## 1) Project goal in one sentence
The project detects leaked secrets in Git history and current source files by combining external secret scanning, normalization, rule-based classification, and an ML-based false-positive filter, then exposing findings through a local API and review dashboard.

## 2) System design we followed

### High-level architecture
The repository is organized around four connected layers:

1. Detection layer
   - Uses Gitleaks as the external secret scanner.
   - Runs as a subprocess and reads its JSON report.
   - Located in [backend/detection/gitleaks_runner.py](../backend/detection/gitleaks_runner.py) and [backend/detection/normalizer.py](../backend/detection/normalizer.py).

2. Classification layer
   - Maps Gitleaks rule IDs to canonical secret types.
   - Assigns a criticality score from a YAML table.
   - Located in [backend/classification/classifier.py](../backend/classification/classifier.py) and [backend/classification/criticality_table.yaml](../backend/classification/criticality_table.yaml).

3. ML filter layer
   - Extracts numeric features from matched secret values and context.
   - Trains a RandomForest classifier.
   - Evaluates baseline A vs baseline B metrics.
   - Located in [backend/ml_filter/features.py](../backend/ml_filter/features.py), [backend/ml_filter/train.py](../backend/ml_filter/train.py), and [backend/ml_filter/evaluate.py](../backend/ml_filter/evaluate.py).

4. Review and persistence layer
   - Stores repositories, scans, findings, and blobs in SQLite.
   - Exposes REST API for UI and automation.
   - Located in [src/shd/walker_api.py](../src/shd/walker_api.py), [src/shd/walker_db.py](../src/shd/walker_db.py), and [frontend/src](../frontend/src).

### Core workflow
The end-to-end flow is:

1. User provides a repository path or URL.
2. The pipeline prepares the repo for local scanning.
3. Gitleaks scans the repository and emits raw findings.
4. Findings are normalized to safe internal objects.
5. Secret type and criticality are assigned.
6. The ML model decides whether the finding should be kept or filtered.
7. Results are persisted and displayed in the dashboard.

This is implemented in [backend/pipeline.py](../backend/pipeline.py).

## 3) What is implemented up to this review

### Implemented and working
- Gitleaks subprocess integration and safe JSON parsing
- Secret hashing and redaction before persistence
- Rule-to-secret mapping and criticality classification
- ML feature extraction and model training script
- Baseline metric generation and validation checks
- SQLite-backed API and dashboard for repository/finding review
- Synthetic Git fixture generation for local evaluation
- Unit/integration tests validating core logic

### Partially implemented / still stubbed
- Risk scoring logic is not fully operational
- Rotation scheduling is still a stub
- Verification adapters remain placeholder logic
- Frontend is local/trusted-only and not production-grade security hardened
- Evaluation is synthetic and not yet strong enough for broad research claims

### Important project files
- Main project readme: [README.md](../README.md)
- Workflow and design docs: [docs/WORKFLOW_M3_TO_M4.md](WORKFLOW_M3_TO_M4.md), [docs/spec_alignment.md](spec_alignment.md), [docs/traceability_matrix.md](traceability_matrix.md)
- Current metrics artifact: [reports/baseline_metrics.json](../reports/baseline_metrics.json)

## 4) How the ML flow works

### Why an ML layer exists
Gitleaks produces many findings, including weak or noisy matches that are not real secrets. The ML layer acts as a false-positive filter. It does not replace scanning; it filters the already-detected candidates.

### How it works in this repo
The model uses a feature vector built from the detected secret string and its context. The actual feature set is defined in [backend/ml_filter/features.py](../backend/ml_filter/features.py):
- entropy
- length
- char_class_count
- digit_ratio
- repeated_char_ratio
- plus context flags such as test-path and placeholder text

The model is trained in [backend/ml_filter/train.py](../backend/ml_filter/train.py) using a RandomForest classifier, and then used in [backend/pipeline.py](../backend/pipeline.py) with a threshold of 0.5.

### Why threshold = 0.5
The model predicts probability of a positive class. If the probability for a real secret is greater than or equal to 0.5, the finding is kept. Otherwise it is discarded. This is a standard binary classifier threshold, chosen for straightforward review operation.

## 5) How the classifier works
The classifier is a rule-based mapping from Gitleaks rule IDs to canonical secret types. The logic is in [backend/classification/classifier.py](../backend/classification/classifier.py).

Examples:
- aws-access-key -> aws_access_key
- github-pat -> github_pat
- slack-token -> slack_token
- generic-high-entropy -> generic_high_entropy

Then the code loads a criticality table from [backend/classification/criticality_table.yaml](../backend/classification/criticality_table.yaml) and assigns a numerical score. This is used to rank findings by severity during review.

## 6) Why the baseline metrics use only certain metrics
The project reports four main metrics for comparison:

- precision
- recall
- F1 score
- false positive rate

These are the standard metrics for evaluating secret-detection quality on a labeled evaluation set. They directly answer:
- How many reported findings are real? (precision)
- How many real secrets were found? (recall)
- Overall balance between both? (F1)
- How many false alarms are generated? (FPR)

### Baseline A and Baseline B
From [backend/ml_filter/train.py](../backend/ml_filter/train.py):
- Baseline A = All Gitleaks findings are treated as positives
- Baseline B = The same test set is evaluated using the ML classifier predictions

This comparison tells us whether the ML layer improves the result over the raw detector baseline.

The actual metrics are stored in [reports/baseline_metrics.json](../reports/baseline_metrics.json).

## 7) Why evaluation is constrained / sometimes blocked
The main issue is not code breaking; it is the validity of the evaluation itself.

The project contains an explicit leakage check in [backend/ml_filter/evaluate.py](../backend/ml_filter/evaluate.py). It looks for a single feature or threshold that can perfectly separate positive and negative labels in the test set.

If such leakage exists, the evaluation is invalid because the model is effectively learning a trivial shortcut rather than a real pattern.

### What the code does
- Builds the test split
- Checks if any single feature can perfectly separate labels
- Marks a warning if leakage is found
- Records `evaluation_valid` and `validation_warning` in the final JSON report

This protects the project from making false scientific claims.

### Current status
The current generated report shows the evaluation is valid for the checked dataset, with no detected single-feature leakage.

That means the model and evaluation are usable for an internal review, but the dataset is still synthetic and should not be treated as a final production benchmark.

## 8) Review status: what is done vs what is next

### Done for this review
- Functional repo scan pipeline
- Gitleaks detection + normalization
- Secret classification + criticality tagging
- ML false-positive filter with measured baseline comparison
- API + database + dashboard
- Synthetic evaluation dataset + validation checks

### Not yet production-ready for final research-grade claim
- Broad external benchmark validation
- Real-world dataset with explicit annotation standards
- Hardened security controls and RBAC
- Full operational risk scoring and rotation workflow
- Production risk model beyond the synthetic demo dataset

## 9) Team split for the current review (4-person model)

### Person 1 – Detection and normalization
Responsible for:
- Gitleaks execution
- JSON parsing and normalization
- Secret hashing / redaction
- Files: [backend/detection/gitleaks_runner.py](../backend/detection/gitleaks_runner.py), [backend/detection/normalizer.py](../backend/detection/normalizer.py)

### Person 2 – Classification and severity logic
Responsible for:
- Rule mapping
- Canonical secret classification
- Criticality assignment
- Files: [backend/classification/classifier.py](../backend/classification/classifier.py), [backend/classification/criticality_table.yaml](../backend/classification/criticality_table.yaml)

### Person 3 – ML model and evaluation
Responsible for:
- Feature design
- Training and model file generation
- Baseline metric comparison
- Leakage checks and validity validation
- Files: [backend/ml_filter/features.py](../backend/ml_filter/features.py), [backend/ml_filter/train.py](../backend/ml_filter/train.py), [backend/ml_filter/evaluate.py](../backend/ml_filter/evaluate.py)

### Person 4 – API, storage, and frontend review layer
Responsible for:
- Repository scan orchestration
- SQLite persistence
- API endpoints and dashboard integration
- Files: [backend/pipeline.py](../backend/pipeline.py), [src/shd/walker_api.py](../src/shd/walker_api.py), [src/shd/walker_db.py](../src/shd/walker_db.py), [frontend/src](../frontend/src)

## 10) Verification evidence
We verified the ML flow with the actual project test suite:

- Command run: `pytest tests/test_ml_filter.py -q`
- Result: 5 passed in 4.85s

This confirms the current ML training, feature extraction, and evaluation scripts are functioning in the checked implementation.

## 11) Suggested explanation for the review presentation
Use this message in the review:

> We implemented the secret-detection pipeline as a layered system: Gitleaks for raw secret detection, normalization for safe internal representation, classification for secret type and severity, and an ML false-positive filter. The current implementation is functional and validated for the synthetic evaluation set, but the scientific evaluation remains bounded by the dataset quality and leakage checks. The project is therefore ready for internal review and demos, but not yet for broad production or benchmark claims without a stronger dataset and deeper validation work.

## 12) Future work
- Replace synthetic validation with larger, properly reviewed test data
- Add stronger model validation and duplicate detection review
- Improve risk scoring and automation
- Build rotation scheduling and verification adapters
- Harden API and UI for multi-user or production deployment
