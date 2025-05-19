ARG BASE_IMAGE=python:3.12-slim

FROM ${BASE_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=.
ENV UV_FROZEN=true
ENV UV_PROJECT_ENVIRONMENT=/venv
ENV UV_CACHE_DIR=/uv_cache
ENV APP_DIR=/app

RUN groupadd -r user && \
        useradd -r -g user user

RUN apt-get update && apt-get install -y \
        curl \
        libffi-dev \
        g++ \
        git && \
        pip install --upgrade pip uv

RUN pip install --upgrade pip uv

WORKDIR ${UV_PROJECT_ENVIRONMENT}
WORKDIR ${UV_CACHE_DIR}
WORKDIR ${APP_DIR}

RUN chown -R user:user ${APP_DIR} ${UV_CACHE_DIR} ${UV_PROJECT_ENVIRONMENT}

COPY pyproject.toml uv.lock ${APP_DIR}/

USER user

RUN uv venv --seed && \
        uv sync --no-dev --no-install-project

COPY . /app

ENTRYPOINT ["uv", "run", "--no-dev", "krill"]
CMD ["-u", "30", "-S", "/app/test_sources.txt"]

FROM base AS prod
RUN uv sync --no-dev

FROM base AS dev-root
RUN uv sync
USER root

FROM dev-root AS dev
USER user
