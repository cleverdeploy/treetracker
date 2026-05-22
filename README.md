# Tree Tracker

Mobile-first web app for cataloguing tagged trees in Stratford-upon-Avon. Sign in with Google, snap a photo, the server extracts the numbered tag (Claude Haiku vision) and GPS (EXIF), and an admin queue gates what appears on the public map.

Live: https://treetracker.wasim.dev

## Local dev

```bash
cp .env.example .env             # fill in secrets
docker compose up                # postgres + app on :8000
```

Or, without docker:

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
pytest
```

## Deploy

GitHub: https://github.com/cleverdeploy/treetracker  
Hosting: Dokploy (`dokploy.cleverdeploy.com`) builds from `Dockerfile`, mounts `/data` for photos, connects to shared Postgres at `postgres.cleverdeploy.com`.

Design doc: [`docs/superpowers/specs/2026-05-22-tree-tracker-design.md`](docs/superpowers/specs/2026-05-22-tree-tracker-design.md)
