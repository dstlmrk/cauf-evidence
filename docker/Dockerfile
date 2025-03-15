FROM node:16 AS node-builder

WORKDIR /app

COPY package.json package-lock.json webpack.config.js ./

RUN npm install

COPY assets /app/assets
RUN npm run build

FROM python:3.13.2-slim AS python-builder

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

FROM python:3.13.2-slim AS runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=python-builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY ultihub /app/ultihub
COPY static /app/static

COPY --from=node-builder /app/static/dist /app/static/dist

WORKDIR /app/ultihub

COPY docker/entrypoint.sh /
ENTRYPOINT ["sh", "/entrypoint.sh"]
