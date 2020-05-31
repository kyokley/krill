FROM python:3.8-slim AS base

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV VIRTUAL_ENV=/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update && apt-get install -y \
        firefox-esr \
        libffi-dev \
        git \
        gcc \
        ca-certificates \
        curl

RUN curl -LO https://github.com/browsh-org/browsh/releases/download/v1.6.4/browsh_1.6.4_linux_amd64.deb && \
        dpkg -i browsh_1.6.4_linux_amd64.deb
RUN curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock

RUN pip install pip --upgrade && \
    /root/.poetry/bin/poetry install --no-dev

CMD ["krill++", "-u", "30", "-S", "/app/test_sources.txt"]

FROM base AS prod
COPY . /app
RUN python setup.py install

FROM base AS dev
RUN /root/.poetry/bin/poetry install

COPY . /app
RUN python setup.py install
