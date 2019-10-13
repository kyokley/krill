FROM python:3.7-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ARG REQS=--no-dev

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

COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock

RUN pip install pip --upgrade && \
    /root/.poetry/bin/poetry install ${REQS}

COPY . /app
RUN python setup.py install

CMD ["krill++", "-u", "30", "-S", "/app/test_sources.txt"]
