FROM node:24-bookworm-slim AS web-build
WORKDIR /app
RUN npm install --global pnpm@11.19.0
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.json ./
RUN pnpm install --frozen-lockfile
COPY apps ./apps
COPY packages ./packages
COPY scripts/generate-scenario-validator.mjs ./scripts/generate-scenario-validator.mjs
RUN pnpm build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    SPONGE_ENVIRONMENT=production \
    SPONGE_HOST=0.0.0.0 \
    SPONGE_PORT=8080 \
    SPONGE_STORAGE_ROOT=/app/data/local \
    SPONGE_WEB_DIST=/app/dist
WORKDIR /app
RUN apt-get update && apt-get install --yes --no-install-recommends ca-certificates libexpat1 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.12.12
COPY pyproject.toml uv.lock alembic.ini ./
RUN uv sync --frozen --no-dev --no-install-project
RUN useradd --create-home --uid 10001 sponge \
    && mkdir -p /app/data/local \
    && chown -R sponge:sponge /app/data
COPY services ./services
COPY packages/contracts ./packages/contracts
COPY scripts ./scripts
COPY infra/migrations ./infra/migrations
COPY --chmod=0555 infra/docker-entrypoint.sh /usr/local/bin/sponge-entrypoint
COPY --from=web-build /app/dist ./dist
COPY data/local/bundles/2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba ./seed/bundles/2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba
USER sponge
EXPOSE 8080
ENTRYPOINT ["sponge-entrypoint"]
CMD ["uvicorn","services.api.main:app","--host","0.0.0.0","--port","8080","--no-server-header","--no-proxy-headers"]
