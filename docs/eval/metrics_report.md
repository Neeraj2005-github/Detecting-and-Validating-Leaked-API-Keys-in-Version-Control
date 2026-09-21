# Metrics Report

This file is a report template for the frozen Week 3 evaluation. Run:

```powershell
pytest --cov=src --cov-report=html --cov-report=term
```

Record the resulting overall and per-secret-type precision, recall, F1, and
finite-candidate FPR here after the dataset manifest is frozen.

## FPR Definition

This project defines FPR as `FP / (TP + FP)`, the false-positive share of
emitted findings. A conventional `FP / (FP + TN)` rate is not used because the
population of non-secret strings in repository history is not enumerable.

## Deferred Objectives

O3-O5 are deferred to Semester VIII and are not silently represented by this
baseline evaluation.