FROM python:3.10


ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_VERSION=1.8.3

RUN pip install --upgrade pip
RUN pip install poetry==$POETRY_VERSION

ENV POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_IN_PROJECT=1 \
  POETRY_VIRTUALENVS_CREATE=0 \
  POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/backend

COPY ./backend/poetry.lock ./backend/pyproject.toml ./
COPY ./common/ ../common/

RUN poetry install && rm -rf $POETRY_CACHE_DIR

COPY ./backend/entrypoint.sh ./
RUN chmod +x ./entrypoint.sh

COPY ../backend/src ./backend

# CMD ["fastapi","dev", "./backend/main.py"]
ENTRYPOINT ["sh", "./entrypoint.sh" ]

