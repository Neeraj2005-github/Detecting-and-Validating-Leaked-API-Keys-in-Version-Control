.PHONY: build test fixture scan baseline clean

build:
	docker build -t secretguard-cp1 .

test:
	python -m pytest -q

fixture:
	python -c "from backend.services.fixture_generator import generate_fixture; generate_fixture()"

scan:
	gitleaks detect --source . --config gitleaks.toml --report-format json --report-path /tmp/secretguard-gitleaks.json --no-banner

baseline:
	python scripts/baseline.py

clean:
	rm -rf .pytest_cache artifacts/_archive/runtime-test
