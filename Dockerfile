FROM python:3.12.3-slim

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN pip install "poetry<1.8.0" && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-root

COPY . /app