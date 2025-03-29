FROM node:16 AS node-builder

WORKDIR /app

COPY package.json package-lock.json webpack.config.js ./

RUN npm install

COPY assets /app/assets
RUN npm run build

FROM python:3.12.5-slim AS python-builder

RUN pip install --no-cache-dir poetry==2.1.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app
COPY ../pyproject.toml ../poetry.lock ./

# Poetry will complain if a README.md is not found
RUN touch README.md

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev --no-root

FROM python:3.12.5-slim AS runtime

# Due to pg_dump
RUN apt-get update && \
    apt-get install -y wget gnupg lsb-release && \
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
