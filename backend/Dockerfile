FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_SYSTEM_PYTHON=1 \
    PATH="/app/backend/.venv/bin:$PATH"

WORKDIR /app

COPY ./backend/pyproject.toml ./backend/uv.lock ./
COPY ./common/ /common/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

COPY ./backend/src ./src
COPY ./backend/tests ./tests
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Change ownership and permissions of config.yaml
RUN chown -R root:root /app/
RUN chmod -R 755 /app/

COPY ./backend/entrypoint.sh .
RUN chmod +x ./entrypoint.sh

CMD [ "sh", "./entrypoint.sh" ]