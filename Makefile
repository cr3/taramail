VENV := .venv

PYTHON := poetry run python
TOUCH := $(PYTHON) -c 'import sys; from pathlib import Path; Path(sys.argv[1]).touch()'

poetry.lock: pyproject.toml
	poetry check --lock

# Build venv with python deps.
$(VENV):
	@echo Building Python virtualenv
	@$(PYTHON) -m venv $@
	@echo Installing Poetry environment
	@poetry install --all-extras
	@$(TOUCH) $@

# Convenience target to build venv
.PHONY: setup
setup: $(VENV)

.PHONY: check
check: $(VENV)
	@echo Checking Poetry lock: Running poetry check --lock
	@poetry check --lock
	@echo Linting code: Running pre-commit
	@poetry run pre-commit run -a

.PHONY: test
test: $(VENV)
	@echo Testing code: Running pytest
	@poetry run coverage run -p -m pytest

.PHONY: coverage
coverage: $(VENV)
	@echo Testing covarage: Running coverage
	@poetry run coverage combine
	@poetry run coverage html --skip-covered --skip-empty
	@poetry run coverage report

.PHONY: docs
docs: $(VENV)
	@echo Building docs: Running sphinx-build
	@poetry run sphinx-build -W -d build/doctrees docs build/html

.PHONY: deploy
deploy:
	@echo Deploying
	@docker compose pull
	@docker compose up --force-recreate --build -d
	@docker image prune -f

.PHONY: undeploy
undeploy:
	@echo Undeploying
	@docker compose down

.PHONY: clean
clean:
	@echo Cleaning ignored files
	@git clean -Xfd

.DEFAULT_GOAL := test
