FROM python:3.12.0rc1-slim

WORKDIR /app

RUN apt update -y && \
    apt-get install gcc libffi-dev -y \
    && pip install pipx && pipx install poetry

COPY poetry.lock pyproject.toml /app/

ENV PATH="/root/.local/bin:/root/.local/pipx/venvs/poetry/bin:${PATH}"
RUN poetry config virtualenvs.create false && poetry install --only cuwb_stream --no-interaction --no-ansi --no-root

COPY ./cuwb_stream/ /app/cuwb_stream

WORKDIR /app

CMD ["python", "-m", "cuwb_stream.tools", "collect"]
