ARG BASE_IMAGE=python:3.12-slim

FROM ${BASE_IMAGE} AS base-builder
ENV POETRY_VENV=/poetry_venv
ENV VIRTUAL_ENV=/venv
RUN python3 -m venv $POETRY_VENV
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH:$POETRY_VENV/bin"

RUN apt-get update && apt-get install -y \
        curl \
        libffi-dev \
        g++ \
        git

RUN $POETRY_VENV/bin/pip install --upgrade pip poetry && \
        pip install --upgrade pip

WORKDIR /app

FROM base-builder AS venv_builder
COPY poetry.lock pyproject.toml /app/

RUN $POETRY_VENV/bin/poetry install --without dev

FROM ${BASE_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV POETRY_VENV=/poetry_venv
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH:$POETRY_VENV/bin"

RUN apt-get update && apt-get install -y \
        git \
        gcc \
        ca-certificates \
        curl

WORKDIR /app

COPY --from=venv_builder $POETRY_VENV $POETRY_VENV
COPY --from=venv_builder $VIRTUAL_ENV $VIRTUAL_ENV
COPY . /app

FROM base AS prod
RUN poetry install --without dev
CMD ["krill", "-u", "30", "-S", "/app/test_sources.txt"]

FROM base AS dev
RUN poetry install
