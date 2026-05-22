# Tree Tracker — deploy handoff

The app is built, tested, pushed, and the database + DNS are ready. Three things remain that need a browser session: **Google OAuth client**, **Dokploy app create**, **first deploy + smoke test**.

## Already done

| | |
|---|---|
| GitHub repo | https://github.com/cleverdeploy/treetracker (public) |
| Live URL (after deploy) | https://treetracker.wasim.dev |
| DNS | A `treetracker.wasim.dev → 178.104.246.72`, DNS-only (Cloudflare zone `6cf371334622ecb6d2eacaae07f7774e`) |
| Postgres DB | `treetracker` on `postgres.cleverdeploy.com` (role `treetracker`, password below) |
| Postgres firewall | dokploy-prod IP already allowlisted (no change needed) |
| CA cert (local copy) | `/tmp/treetracker-pg-ca.crt` |

## Secrets

| Var | Value |
|---|---|
| `treetracker` DB password | `cf59d4a06dd479009efb4824282876bae0a72fe9b76cc824` |
| `SESSION_SECRET` (suggested) | `c68faad3782b1bb931dc61c4ba5434c8c31c56bcf3842f102977daa59ed2590d` |

## Step 1 — Google OAuth client (≈3 min)

1. Open https://console.cloud.google.com/apis/credentials.
2. Pick (or create) a project — e.g. reuse an existing personal one.
3. **Configure consent screen** (if not already): External, app name "Tree Tracker", support email = yours, scopes `openid email profile`, test users empty (External + production after publishing).
4. **Create credentials → OAuth client ID → Web application**, name "Tree Tracker prod".
   - Authorized JavaScript origins: `https://treetracker.wasim.dev`
   - Authorized redirect URIs: `https://treetracker.wasim.dev/auth/callback`
5. Copy the **Client ID** and **Client secret** — you'll paste them into Dokploy in step 2.

## Step 2 — Create the Dokploy app (≈5 min)

1. Open https://dokploy.cleverdeploy.com → sign in (`wasim.juned@gmail.com`).
2. **Projects → Create Project**, name `treetracker`.
3. **Create Service → Application**, name `treetracker-web`.
4. **Provider tab → Git**:
   - Repository URL: `https://github.com/cleverdeploy/treetracker.git`
   - Branch: `main`
   - Build path: `/`
   - Build type: **Dockerfile** (it should auto-detect).
5. **Environment tab — paste this block**:

   ```
   DATABASE_URL=postgresql+psycopg://treetracker:cf59d4a06dd479009efb4824282876bae0a72fe9b76cc824@postgres.cleverdeploy.com:5432/treetracker?sslmode=verify-ca&sslrootcert=/run/secrets/pg-ca.crt
   SESSION_SECRET=c68faad3782b1bb931dc61c4ba5434c8c31c56bcf3842f102977daa59ed2590d
   GOOGLE_CLIENT_ID=<paste from step 1>
   GOOGLE_CLIENT_SECRET=<paste from step 1>
   OAUTH_REDIRECT_URL=https://treetracker.wasim.dev/auth/callback
   ANTHROPIC_API_KEY=<your Anthropic API key>
   ADMIN_EMAILS=wasim.juned@gmail.com
   PHOTOS_DIR=/data/photos
   BASE_URL=https://treetracker.wasim.dev
   ```

6. **Advanced → Volumes**: add a **named volume** — name `treetracker-photos`, mount path `/data/photos`.
7. **Advanced → Files** (or "Secret Files" / "Mounts"): mount the CA cert.
   - Filename: `/run/secrets/pg-ca.crt`
   - Contents: paste the contents of `/tmp/treetracker-pg-ca.crt` (the full `-----BEGIN CERTIFICATE-----…END CERTIFICATE-----` block).
8. **Domains → Add Domain**:
   - Host: `treetracker.wasim.dev`
   - Container Port: `8000`
   - HTTPS: ON
9. **Deploy** (top right). Watch the logs — the entrypoint runs `alembic upgrade head` then starts uvicorn. First Docker build is ~3 min.

## Step 3 — Smoke test (≈2 min)

1. `curl -s https://treetracker.wasim.dev/healthz` → `{"ok":true}`.
2. Open `https://treetracker.wasim.dev` on a phone (or desktop): map of Stratford-upon-Avon should load with no pins.
3. Sign in with Google → admin nav should show (because your email is in `ADMIN_EMAILS`).
4. **Add → take a photo of a tree** (or use a saved one). Submit. If the photo has no GPS the pin-drop step appears.
5. Open **Queue** → approve the sighting with the correct tag number.
6. Reload the map — your new pin should appear.

## If anything blows up

- **OAuth callback errors:** check that the redirect URI in Google Cloud Console exactly matches `https://treetracker.wasim.dev/auth/callback`, no trailing slash.
- **`alembic upgrade head` fails on first boot:** check the CA cert mount path and that `DATABASE_URL` has `sslmode=verify-ca&sslrootcert=/run/secrets/pg-ca.crt`.
- **Photo uploads fail with 502:** the named volume isn't mounted or `PHOTOS_DIR` is wrong — both must agree on `/data/photos`.
- **Haiku OCR returning null tags:** check `ANTHROPIC_API_KEY` set; logs will show the raw call.
