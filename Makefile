PYTHON = python3
PYTEST = pytest
PIP = pip

.PHONY: all test install clean

all: test

test:
	$(PYTEST) tests/test_sandbox.py

install:
	$(PIP) install -r requirements.txt

clean:
	find . -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache