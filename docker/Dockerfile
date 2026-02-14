FROM node:16 AS node-builder

WORKDIR /app

COPY package.json package-lock.json webpack.config.js ./

RUN npm install

COPY assets /app/assets
RUN npm run build

FROM python:3.12.5-slim AS python-builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY ../pyproject.toml ../uv.lock ./

# hatchling requires README.md to exist
RUN touch README.md

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12.5-slim AS runtime

# Due to pg_dump and compilemessages
RUN apt-get update && \
    apt-get install -y wget gnupg lsb-release gettext && \
    echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt-get update && \
    apt-get install -y postgresql-client-16 && \
    rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=python-builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY ultihub /app/ultihub
COPY static /app/static

COPY --from=node-builder /app/static/dist /app/static/dist

WORKDIR /app/ultihub

COPY docker/entrypoint.sh /
ENTRYPOINT ["sh", "/entrypoint.sh"]
