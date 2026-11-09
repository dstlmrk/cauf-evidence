FROM node:26@sha256:438603bbb5cda404b9416f0b5c8026f61501ab911760d861ec28c36b5d675725 AS node-builder

WORKDIR /app

COPY package.json package-lock.json webpack.config.js ./

RUN npm install

COPY assets /app/assets
RUN npm run build

FROM python:3.14-slim AS python-builder

# Install uv
COPY --from=astral/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY ../pyproject.toml ../uv.lock ./

# hatchling requires README.md to exist
RUN touch README.md

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.14-slim AS runtime

# Due to pg_dump
RUN apt-get update && \
    apt-get install -y wget && \
    install -d /usr/share/postgresql-common/pgdg && \
    wget --quiet -O /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    . /etc/os-release && \
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list && \
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
