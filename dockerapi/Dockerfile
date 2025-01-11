ARG PYTHON_VERSION=3
FROM python:${PYTHON_VERSION}-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.8.4 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

FROM base AS build

ENV PATH="$POETRY_HOME/bin:$PATH"

RUN apt update \
  && apt install -y --no-install-recommends curl build-essential \
  && curl -sSL https://install.python-poetry.org | python3 -

WORKDIR /app
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-dev --extras dockerapi

FROM base AS runtime

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY --from=build /app ./
COPY ./taram ./taram

EXPOSE 80
CMD ["uvicorn", "--host=0.0.0.0", "--port=80", "taram.dockerapi:app"]
