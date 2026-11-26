.PHONY: build test fixture scan baseline clean

build:
	python scripts/baseline.py build

test:
	python scripts/baseline.py test

fixture:
	python scripts/baseline.py fixture

scan:
	python scripts/baseline.py scan

baseline:
	python scripts/baseline.py baseline

clean:
	python scripts/baseline.py clean
