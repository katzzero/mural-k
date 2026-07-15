# AGENTS.md

## Project Overview

Self-hosted Kanban board: Flask + SQLite backend, single-file vanilla JS frontend, Alpine Docker image.

## Structure

```
backend/app.py      # Entire backend (372 lines, single file)
frontend/index.html # Entire frontend (1073 lines, HTML+CSS+JS all inline)
Dockerfile          # Alpine-based, multi-arch (amd64+arm64)
```

No build step. No package manager. No bundler. Frontend is served as a static file by Flask.

## Running Locally

```bash
cd mural-k
pip install -r backend/requirements.txt
python backend/app.py
# Server at http://localhost:5000
```

Frontend path is resolved at `app.py:7-9` via env `KANBAN_FRONTEND` or auto-detected (`/app/frontend` in Docker, `../frontend` locally).

Database path is resolved at `app.py:14-16` via env `KANBAN_DB` or auto-detected (`/data/k.sqlite` in Docker, `../data/k.sqlite` locally).

## Docker

```bash
docker build -t mural-k .
docker run -d -p 8080:5000 -v mural-k-data:/data --name mural-k mural-k
```

Container exposes port 5000 (mapped to 8080). Data persists in `/data/k.sqlite`.

## CI/CD

`.github/workflows/docker-push.yml` triggers on:
- Push to `main` → pushes `katzzero/mural-k:latest`
- Push tag `v*` → pushes semver tags (`v1.2.3`, `1.2`, `1`)

Docker Hub credentials stored in secrets `DOCKER_USERNAME` / `DOCKER_PASSWORD`.

## Key Gotchas

- **Race condition on order_index**: `MAX(order_index)+1` in create endpoints is not atomic. Concurrent requests can produce duplicate order values.
- **Frontend is monolithic**: All JS/CSS is inline in `index.html`. No modules, no imports, all globals. Any edit affects the full 1077 lines.

## API Notes

- All endpoints return JSON (except DELETE which returns 204 empty).
- `GET /api/cards` returns all non-trashed cards (used by frontend to avoid N+1 queries).
- `POST /api/reset` wipes everything and re-creates 3 default columns (Portuguese names: "A Fazer", "Em Andamento", "Concluído").
- `DELETE /api/cards/:id` soft-deletes (sets `trashed=1`). Use `/api/cards/trash/clear` for hard delete.

## Env Vars

| Variable | Default | Description |
|----------|---------|-------------|
| `KANBAN_FRONTEND` | `/app/frontend` (Docker) or `../frontend` | Path to frontend files |
| `KANBAN_DB` | `/data/k.sqlite` (Docker) or `../data/k.sqlite` | SQLite database path |
