# Supply chain controls

Native Gitleaks is pinned to `8.18.4`. The Docker image verifies a release archive checksum before extraction and runs as UID `10001`.

The scan container is expected to be invoked with:

```text
docker run --rm --network none --read-only --memory 1g --pids-limit 256 \
  -v "$PWD":/repo:ro secretguard-cp1 ...
```

Python dependencies are declared in `requirements.txt`; JavaScript dependencies use `package-lock.json` and `frontend/package-lock.json`. Audit evidence is recorded under `docs/evidence/`.
