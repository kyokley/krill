FROM frolvlad/alpine-python3

RUN apk add --no-cache \
        libffi-dev \
		git \
        gcc \
	    ca-certificates \
        musl-dev \
        openssl-dev \
        python3-dev

COPY . /app

WORKDIR /app
RUN pip install .

CMD ["krill++", "-u", "30", "-S", "/app/test_sources.txt"]
