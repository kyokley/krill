ARG BASE_IMAGE=python:3.12-alpine

FROM ${BASE_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=.
ENV UV_FROZEN=true
ENV UV_PROJECT_ENVIRONMENT=/venv
ENV UV_CACHE_DIR=/uv_cache
ENV APP_DIR=/app

RUN addgroup user && adduser -SG user user

FROM base AS builder

RUN apk update && apk add --no-cache \
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

FROM base AS dev_or_prod
RUN pip install --upgrade pip uv
COPY pyproject.toml uv.lock ${APP_DIR}/
COPY --from=builder ${UV_PROJECT_ENVIRONMENT} ${UV_PROJECT_ENVIRONMENT}
WORKDIR /app

FROM dev_or_prod AS prod

COPY . /app
RUN uv sync --no-dev

ENTRYPOINT ["uv", "run", "--no-dev", "krill"]
CMD ["-u", "30", "-S", "/app/test_sources.txt"]

FROM dev_or_prod AS dev-root
RUN uv sync --no-install-project
COPY . /app
RUN uv sync
USER root

FROM dev-root AS dev
USER user
