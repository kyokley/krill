FROM python:3.7-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ARG REQS=--no-dev

ENV VIRTUAL_ENV=/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apk update && apk add --no-cache \
        libffi-dev \
        git \
        gcc \
        ca-certificates \
        musl-dev \
        openssl-dev \
        curl

RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock

RUN pip install pip --upgrade && \
    /root/.poetry/bin/poetry install ${REQS}

COPY . /app
CMD ["krill++", "-u", "30", "-S", "/app/test_sources.txt"]
