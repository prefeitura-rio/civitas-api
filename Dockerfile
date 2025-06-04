FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN pip install "poetry<1.8.0" && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libglib2.0-0 \
    libcairo2 \
    libharfbuzz0b \
    libffi-dev \
    shared-mime-info \
    git \
    firefox-esr && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . /app
COPY ./scripts/* /app/