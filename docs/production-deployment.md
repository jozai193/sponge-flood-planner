# SPONGE production deployment

This package deploys the application as an evidence-bounded flood-screening and green-infrastructure planning tool. Production hardening does not turn uncalibrated terrain, rainfall, drainage, cost or eligibility assumptions into validated engineering evidence. The UI and exports continue to identify those limits.

## Services

- `api` serves the compiled single-page app and `/api/v1`, adds security headers, restricts accepted hosts and rate-limits anonymous session creation.
- `worker` runs bounded preparation and evidence jobs outside the request process.
- `maintenance` redelivers durable queued rows, reconciles stale jobs and removes expired private artifacts only when no resource still references them.
- PostgreSQL/PostGIS stores sessions and immutable resource metadata.
- Redis transports queues and public rate counters. PostgreSQL remains the source of truth for job state; Redis uses `noeviction` so queue keys are never discarded to satisfy its memory ceiling.
- The `sponge-data` volume stores bundles, imports, enrichment outputs and provider caches. The image seeds the immutable Spring Garden sample on first start.

## Configure and start

Use a long random database password. Do not commit it to `.env` or source control.

```powershell
$env:SPONGE_DB_PASSWORD = '<long-random-password>'
$env:SPONGE_TRUSTED_HOSTS = 'sponge.example.org,localhost,127.0.0.1'
$env:SPONGE_ALLOWED_ORIGINS = 'https://sponge.example.org'
$env:SPONGE_TRUSTED_PROXY_CIDRS = '127.0.0.1/32'
docker compose -f infra/compose/compose.production.yaml up --build -d --wait
```

The compose file publishes `127.0.0.1:8080` by default. Terminate TLS at a reverse proxy and forward to that address. Forward the original `Host` and append (do not replace) `X-Forwarded-For`. Add the public hostname plus `localhost,127.0.0.1` to `SPONGE_TRUSTED_HOSTS`; the loopback entries are required by the container health check. Set `SPONGE_TRUSTED_PROXY_CIDRS` to only the proxy address or network as seen by the API. Uvicorn's generic proxy-header rewriting is disabled; the application ignores forwarding headers from every other peer. `infra/nginx/sponge.conf.example` is a starting configuration and includes the matching 102 MB outer body limit. Same-origin hosting needs no CORS origin; list only explicit HTTPS origins when a separate frontend is intentional.

The ASGI layer rejects oversized bodies while they stream, before FastAPI parses or spools multipart data. Ordinary API bodies are capped at 25 MB, survey imports at 10.1 MB including transport overhead, and terrain requests at 102 MB with a second 100 MB file-content check.

Check the service without creating a user session:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/api/v1/health
Invoke-RestMethod http://127.0.0.1:8080/api/v1/ready
$env:SPONGE_BASE_URL = 'http://127.0.0.1:8080'
pnpm smoke:production
```

`health` confirms that the process is alive. `ready` also checks PostgreSQL and Redis. Container health uses `ready`. The browser smoke verifies that the strict production CSP still permits the compiled application to render, that the judge tour opens, that the prepared demo becomes interactive, and that no console or page errors occur.

## Operations

- Back up `pgdata`, `redisdata` and `sponge-data` together. Database metadata points at immutable files in `sponge-data`; restoring only one side can leave incomplete resources.
- Apply upgrades with `docker compose ... up --build -d --wait`. The one-shot `migrate` service runs Alembic before API and worker startup.
- Keep provider and Earthdata credentials server-side using `SPONGE_EE_*` and `SPONGE_EARTHDATA_TOKEN`. Never use a `VITE_` prefix for secrets.
- Set `SPONGE_SESSION_LIMIT_PER_HOUR` for the expected judge or public traffic. Per-session preparation and enrichment concurrency limits still apply.
- Private sessions expire after `SPONGE_SESSION_TTL_HOURS` (seven days by default). The browser obtains one replacement session when an expired token is encountered. Every `SPONGE_RETENTION_INTERVAL_SECONDS` (60 seconds by default), maintenance removes expired database rows, evidence directories, stale staging directories and only those bundle directories that have no surviving private or public reference; it also redelivers durable queued jobs.
- CPU references run in isolated child processes with `SPONGE_CPU_REFERENCE_CONCURRENCY` capacity and a hard `SPONGE_CPU_REFERENCE_TIMEOUT_SECONDS` deadline.
- Monitor API health, worker presence, queue depth, PostgreSQL disk, Redis memory and the persistent data volume. Provider outages are expected to degrade acquisition paths without invalidating the bundled demo.

## Release verification

Before deployment, run:

```powershell
pnpm install --frozen-lockfile
pnpm audit --prod
.bootstrap/Scripts/uv.exe export --frozen --no-dev --format requirements-txt --output-file output/requirements-audit.txt
.bootstrap/Scripts/uv.exe tool run pip-audit --no-deps --disable-pip -r output/requirements-audit.txt
pnpm test
pnpm build
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m scripts.export_contracts --check
.venv/Scripts/ruff.exe check services scripts tests
.venv/Scripts/mypy.exe
pnpm test:browser
$env:SPONGE_BASE_URL = 'http://127.0.0.1:8080'
pnpm smoke:production
```

The browser suite expects the local PostgreSQL, Redis, API and worker services from `Start-SPONGE.ps1`. A green software release does not upgrade the documented observational-validation status. Review `docs/hackathon-build/implementation-status.json` and report assumptions before representing results externally.
