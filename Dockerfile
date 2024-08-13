FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN pip install "poetry<1.8.0" && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

COPY . /app
COPY ./scripts/* /app/