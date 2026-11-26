FROM node:26@sha256:e18c3ccdf7d71619990b0e85639f506e2028a95410999cab24cc373cbd10e0ac AS node-builder

WORKDIR /app

COPY package.json package-lock.json webpack.config.js ./

RUN npm install

COPY assets /app/assets
RUN npm run build

FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS python-builder

# Install uv
COPY --from=astral/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY ../pyproject.toml ../uv.lock ./

# hatchling requires README.md to exist
RUN touch README.md

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS runtime

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
