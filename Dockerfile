FROM python:3.8-slim AS venv_builder
ENV VIRTUAL_ENV=/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PATH="$PATH:/root/.poetry/bin"

RUN apt-get update && apt-get install -y \
        curl \
        git

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock

RUN pip install pip --upgrade && \
    /root/.poetry/bin/poetry install --no-dev


FROM python:3.8-slim AS base

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV VIRTUAL_ENV=/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PATH="$PATH:/root/.poetry/bin"

RUN apt-get update && apt-get install -y \
        git \
        gcc \
        ca-certificates \
        curl

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock
COPY --from=venv_builder /venv /venv

CMD ["krill++", "-u", "30", "-S", "/app/test_sources.txt"]

FROM base AS prod
COPY . /app
RUN python setup.py install

FROM base AS dev
RUN /root/.poetry/bin/poetry install

COPY . /app
RUN python setup.py develop
