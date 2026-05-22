# Tree Tracker — Design

A mobile-first web app for cataloguing tagged trees in Stratford-upon-Avon. Users sign in with Google, take a photo of a tree, and the app extracts the numbered tag (via Claude Haiku vision) and GPS (from EXIF) and saves a sighting. An admin approval queue gates what appears on the public map. Deployed at `treetracker.wasim.dev`.

## Goals & non-goals

**Goals**
- Mobile-first capture flow: open camera, submit, done.
- Server-side extraction of tag number and GPS so the client stays thin.
- Public read-only map of approved trees; private moderation queue.
- One pin per real-world tree, gallery of sightings over time.

**Non-goals (v1)**
- Offline submission queue (PWA caches the read-only map, not uploads).
- Mobile native app.
- Public-facing leaderboards or social features.
- Tree species identification.

## Stack

- **Backend:** FastAPI (Python 3.12), Uvicorn, SQLAlchemy 2.x, Authlib (Google OAuth), Pillow + pillow-heif (EXIF, thumbnails, HEIC), Anthropic SDK (Haiku 4.5 vision).
- **Frontend:** Jinja2 templates, vanilla JS, Leaflet + OSM tiles, no build step. PWA manifest + service worker for install-to-home-screen.
- **Database:** Existing shared Postgres at `postgres.cleverdeploy.com` (TLS, scram-sha-256). New database `treetracker`.
- **Photo storage:** Files on a Docker volume mounted at `/data/photos/` in the container.
- **Hosting:** Dokploy at `dokploy.cleverdeploy.com`, app domain `treetracker.wasim.dev`.

## Architecture

```
[phone camera] ──HTTPS──▶ FastAPI ──┬─▶ Pillow (EXIF GPS, thumbnail)
                                    ├─▶ Anthropic API (Haiku 4.5 vision → tag#, conf)
                                    ├─▶ /data/photos/ (volume)
                                    └─▶ Postgres (TLS to postgres.cleverdeploy.com)
                                            │
[map page] ◀──GeoJSON──── FastAPI ◀─────────┘
```

Single process. Synchronous request handling for uploads is acceptable (Haiku call is the long pole at a few seconds — the user sees a "Submitted — awaiting review" screen on success, no live preview of OCR output).

## Components

**Backend (`app/`)**
- `main.py` — FastAPI app factory, routes wiring, static + template mount.
- `auth.py` — Google OAuth login/logout/callback, signed session cookie, `current_user` dependency, `require_admin` dependency (admin allowlist by email in env).
- `db.py` — SQLAlchemy engine + session, TLS to `postgres.cleverdeploy.com`.
- `models.py` — `User`, `Tree`, `Sighting`, `AuditLog`.
- `routes/pages.py` — `/` (map), `/trees/{id}` (detail), `/submit` (upload form), `/admin` (queue).
- `routes/api.py` — `POST /api/sightings` (multipart upload), `PATCH /api/sightings/{id}/location` (drop pin), `GET /api/trees.geojson`, `GET /api/trees/{id}`, admin `POST /api/sightings/{id}/approve`, `POST /api/sightings/{id}/reject`.
- `ingest.py` — orchestrates one upload: store file → EXIF GPS → Haiku OCR → create Sighting → return id.
- `exif.py` — Pillow-based GPS extraction, returns `(lat, lon)` or `None`.
- `ocr.py` — Anthropic SDK call with Haiku 4.5, returns `{tag: str|None, confidence: 0..1}`.
- `storage.py` — write original + 1200px JPEG thumb to `/data/photos/<sighting_id>/`.
- `moderation.py` — approve/reject helpers, tree find-or-create, aggregate recompute.

**Frontend (`app/templates/` + `app/static/`)**
- `base.html` — PWA shell, manifest link, mobile viewport, top nav (Map / Add / Admin if admin).
- `index.html` — Leaflet map centered on Stratford-upon-Avon (`52.1917, -1.7080`, zoom 14), OSM tiles, fetches `/api/trees.geojson`.
- `tree.html` — header (tag #, canonical location, first/last seen), photo gallery, sightings list with comments.
- `submit.html` — `<input type="file" accept="image/*" capture="environment">`, preview, optional comment, fallback Leaflet pin-drop when GPS missing, optional manual tag entry, submit.
- `admin.html` — sighting queue: thumbnail, detected tag + confidence, GPS, comment, submitter; edit final tag, move pin, approve, or reject with reason.
- `static/map.js`, `static/submit.js`, `static/admin.js`, `static/sw.js`, `manifest.webmanifest`, icons.

**Infra**
- `Dockerfile` — `python:3.12-slim`, system deps for pillow-heif (`libheif1`), non-root user, uvicorn on port 8000.
- `compose.yml` — local dev only.
- Dokploy app config: env vars (see below), `/data` volume, Traefik label → `treetracker.wasim.dev`.

## Data model

```sql
users (
  id              uuid pk,
  google_sub      text unique not null,
  email           text not null,
  name            text,
  picture_url     text,
  is_admin        boolean not null default false,
  created_at      timestamptz not null default now()
)

trees (
  id              uuid pk,
  tag_number      text unique not null,        -- canonical, digits-only, leading zeros preserved
  canonical_lat   double precision,            -- mean of approved sightings' lat
  canonical_lon   double precision,
  first_seen_at   timestamptz not null,
  last_seen_at    timestamptz not null,
  sighting_count  int not null default 0       -- approved sightings only
)

sightings (
  id              uuid pk,
  tree_id         uuid references trees(id),   -- null until approved
  user_id         uuid references users(id) not null,
  photo_path      text not null,               -- /data/photos/<id>/original.<ext>
  thumb_path      text not null,
  lat             double precision,
  lon             double precision,
  gps_source      text not null,               -- 'exif' | 'manual' | 'none'
  detected_tag    text,                        -- Haiku raw output
  detected_conf   real,                        -- 0..1
  final_tag       text,                        -- set on approval; admin can correct
  comment         text,
  status          text not null default 'pending',  -- pending | approved | rejected
  reject_reason   text,
  created_at      timestamptz not null default now(),
  reviewed_at     timestamptz,
  reviewed_by     uuid references users(id)
)

audit_log (
  id              bigserial pk,
  actor_user_id   uuid,
  action          text not null,
  target_type     text,
  target_id       text,
  payload         jsonb,
  created_at      timestamptz not null default now()
)
```

Indexes: `sightings(status, created_at)` for the queue; `sightings(tree_id)` for galleries; `trees(tag_number)` already unique.

Migrations via Alembic.

## Key flows

### Upload
1. User taps **Add Tree** → camera input opens.
2. Client previews image + optional comment, submits multipart POST to `/api/sightings`.
3. Server writes the original to `/data/photos/<sighting_id>/original.<ext>` and generates a 1200px thumbnail.
4. `exif.extract_gps()` — if present, `gps_source='exif'`. If missing, response is `{id, needs_location: true}`; client opens a Leaflet pin-drop and `PATCH`es `/api/sightings/{id}/location` with `gps_source='manual'`.
5. `ocr.read_tag()` — Haiku 4.5 vision, JSON-mode prompt requesting the visible numbered tag and a 0..1 confidence. If `confidence < 0.7` or no number, sighting saves with the raw output and a "needs tag review" flag for the queue. Anthropic failure → save with `detected_tag=null`; do not block submission.
6. Sighting row inserted with `status='pending'`. User sees "Submitted — awaiting review."

### Moderation
1. `/admin` lists pending sightings, newest first.
2. Admin can edit `final_tag`, edit GPS (move pin), approve, or reject (with reason).
3. On approve: find-or-create `Tree` by `final_tag` (normalized: strip non-digits, preserve leading zeros), set `sighting.tree_id`, recompute `canonical_lat/lon` as mean of approved sightings' lat/lon, update `sighting_count` and `last_seen_at`, write audit log.
4. On reject: set `status='rejected'`, `reject_reason`, write audit log. Files retained for 30 days then purged by a cron job (out of scope for v1 — manual purge for now).

### Public map
1. `/` loads Leaflet at Stratford-upon-Avon center, OSM tiles.
2. Fetches `/api/trees.geojson` — approved trees only, with `properties.tag_number`, `properties.thumb_url` (most recent approved sighting), `properties.sighting_count`.
3. Tap pin → popup with tag # and thumbnail → link to `/trees/{id}`.
4. Marker clustering with Leaflet.markercluster when feature count exceeds ~100.

### Tree detail
- Header: Tag #N, canonical location (lat/lon + small static map snippet), first/last seen, sighting count.
- Photo gallery: all approved sightings, newest first, with submitter name and comment.

## Auth

- Google OAuth via Authlib, scopes `openid email profile`.
- Session = signed cookie containing user id (itsdangerous). 30-day expiry, sliding.
- On first sign-in, create `users` row. If email is in `ADMIN_EMAILS` env (comma-separated), set `is_admin=true` on creation; admins added later require a manual DB update (v1 — admin self-service is out of scope).
- All `/api/sightings*` POST/PATCH endpoints require a session. `/admin*` requires `is_admin=true`.

## Configuration (env vars)

| Var | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://…@postgres.cleverdeploy.com:5432/treetracker?sslmode=verify-ca&sslrootcert=/run/secrets/pg-ca.crt` |
| `SESSION_SECRET` | itsdangerous signing key |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth credentials |
| `OAUTH_REDIRECT_URL` | `https://treetracker.wasim.dev/auth/callback` |
| `ANTHROPIC_API_KEY` | for Haiku vision |
| `ADMIN_EMAILS` | comma-separated allowlist, seeds `is_admin=true` |
| `PHOTOS_DIR` | `/data/photos` |
| `BASE_URL` | `https://treetracker.wasim.dev` |

Postgres CA cert mounted via Dokploy secret to `/run/secrets/pg-ca.crt`.

## Error handling & limits

- Max upload: **15 MB**, enforced by FastAPI middleware + Traefik.
- Accepted MIME: `image/jpeg`, `image/heic`, `image/png`. HEIC converted to JPEG server-side via pillow-heif.
- Anthropic API failure → store sighting with `detected_tag=null`, surface in queue for manual entry. Do not block submission.
- Postgres unreachable → 503 with retry banner; client retains the file on the form and retries.
- Per-user rate limit: **30 uploads/hour** via in-process counter (single-VM is fine).
- Photo paths served via a FastAPI route, not statically — gives us auth checks and the ability to swap to S3 later without URL changes.

## Testing

- **Unit (pytest):**
  - `exif.py` — fixture JPEGs with and without GPS, including malformed EXIF.
  - `ocr.py` — Anthropic client mocked; assert prompt shape, parsing of well-formed and malformed responses.
  - `ingest.py` — happy path, missing-GPS path, OCR-failure path, file-write-failure path.
  - `moderation.py` — find-or-create tree by tag, canonical lat/lon recompute, audit log writes.
- **Integration:** one end-to-end test using `httpx.AsyncClient` — upload a fixture photo, assert rows, approve, assert `/api/trees.geojson` includes the tree.
- **Manual smoke:** Playwright at iPhone-12 viewport against the deployed staging URL before promoting.

## Deployment

1. Create GitHub repo `cleverdeploy/treetracker`, push initial code.
2. In Dokploy: create application, point at GitHub repo, set Dockerfile build, attach `/data` volume, set env vars + Postgres CA secret, configure Traefik domain `treetracker.wasim.dev` with Let's Encrypt.
3. Cloudflare DNS: A record `treetracker.wasim.dev → 178.104.246.72`, DNS-only (grey cloud) so LE HTTP-01 resolves.
4. Create the `treetracker` database in shared Postgres and grant the app role.
5. Run Alembic migrations on first deploy (via container entrypoint).
6. Smoke-test upload on real device.

## Open questions for implementation

- None blocking. Resolve at code time: exact Haiku prompt wording, marker-cluster threshold, HEIC handling for screens (probably serve the converted JPEG, retain original).
