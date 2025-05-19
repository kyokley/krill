ARG BASE_IMAGE=python:3.12-slim

FROM ${BASE_IMAGE} AS base-builder
ENV UV_PROJECT_ENVIRONMENT=/venv

RUN apt-get update && apt-get install -y \
        curl \
        libffi-dev \
        g++ \
        git

RUN pip install --upgrade pip uv

WORKDIR /app

FROM base-builder AS venv_builder
COPY pyproject.toml /app/

RUN uv venv --seed && \
        uv sync --no-dev

FROM ${BASE_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=.
ENV UV_PROJECT_ENVIRONMENT=/venv

RUN apt-get update && apt-get install -y \
        git \
        gcc \
        ca-certificates \
        curl && \
        pip install --upgrade pip uv

WORKDIR /app

RUN groupadd -r user && \
        useradd -r -g user user && \
        chown -R user:user /app

COPY --from=venv_builder $UV_PROJECT_ENVIRONMENT $UV_PROJECT_ENVIRONMENT

COPY pyproject.toml /app/
RUN uv sync
COPY . /app

FROM base AS prod
RUN uv sync --no-dev
USER user
ENTRYPOINT ["krill"]
CMD ["-u", "30", "-S", "/app/test_sources.txt"]

FROM base AS dev-root
RUN uv sync
ENTRYPOINT ["krill"]

FROM dev-root AS dev
USER user
