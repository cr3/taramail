VENV := .venv

PYTHON := poetry run python
TOUCH := $(PYTHON) -c 'import sys; from pathlib import Path; Path(sys.argv[1]).touch()'

# Build .venv with deps.
$(VENV): poetry.lock
	@echo "==> Building Python virtualenv..."
	@$(PYTHON) -m venv $@
	@echo "==> Installing Poetry environment..."
	@poetry install
	@$(TOUCH) $@

# Convenience target to build venv
.PHONY: setup
setup: $(VENV)

.PHONY: check
check: $(VENV)
	@echo "==> Checking Poetry lock..."
	@poetry check --lock
	@echo "==> Linting Python code..."
	@poetry run ruff check .

.PHONY: test
test: $(VENV)
	@echo "==> Testing Python code..."
	@poetry run coverage run -p -m pytest

.PHONY: coverage
coverage: $(VENV)
	@echo "==> Checking coverage..."
	@poetry run coverage combine
	@poetry run coverage html --skip-covered --skip-empty
	@poetry run coverage report

.PHONY: docs
docs: $(VENV)
	@echo "==> Building docs..."
	@poetry run sphinx-build -W -d build/doctrees docs build/html

.DEFAULT_GOAL := test
