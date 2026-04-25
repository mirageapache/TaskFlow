# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Monorepo with two services and a separate planning-doc package:

- `backend/` — Django 5 + Django REST Framework API (Python 3.13). Apps live under `backend/apps/<name>/` and project config under `backend/config/`.
- `frontend/` — Vue 3 + TypeScript + Vite SPA. PrimeVue (Aura theme) + TailwindCSS for UI; Pinia for state; Axios via `src/api/client.ts`.
- `.doc/` — Authoritative design documents (Traditional Chinese). When implementing a feature, the matching `.doc/taskflow-*.md` file usually contains the full spec referenced by code comments (e.g. `Phase 1 TDD 階段...詳見 .doc/taskflow-frontend.md §4.5`). Treat these as the source of truth for unimplemented behaviour.
- `docker-compose.dev.yml` — Dev orchestration. Backend on `:8000`, frontend on `:5273` (note: not Vite's default 5173 — `vite.config.ts` overrides it).

The repo is in **Phase 1 MVP scaffolding state**: most app modules contain only `apps.py` + an empty `models.py`. Real implementation is expected to be driven by the TDD plan in `.doc/taskflow-testing.md` and the spec docs.

## Common commands

### Backend (run from `backend/`)

```bash
python -m venv venv && source venv/Scripts/activate   # Windows bash
pip install -r requirements.txt
cp .env.example .env                                  # then edit
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Tests (pytest-django + factory-boy — not yet installed; install before running):

```bash
pytest                                                # all tests
pytest tests/test_tasks/test_views.py                 # one file
pytest tests/test_tasks/test_views.py::TestTaskCreateAPI::test_create_task_success
pytest --cov=apps --cov-report=term-missing
pytest --create-db                                    # force-rebuild test DB (default reuses)
```

Health probe (no JWT required): `GET /api/v1/health/` → returns `{status, db}`.

### Frontend (run from `frontend/`)

```bash
npm install
cp .env.example .env.local
npm run dev          # Vite on http://localhost:5273
npm run build        # vue-tsc --noEmit && vite build
npm run type-check   # vue-tsc --noEmit only
```

Vitest is referenced in `.doc/taskflow-testing.md` but not yet wired into `package.json` — adding `test` scripts and `vitest.config.ts` is part of the Phase 1 setup task.

### Full-stack via Docker

```bash
docker compose -f docker-compose.dev.yml up --build
```

## Architecture notes that span multiple files

### Database fallback in `backend/config/settings.py`

When `DB_HOST` is empty in `.env`, settings.py silently falls back to local SQLite (`backend/db.sqlite3`). With `DB_HOST` set, it switches to PostgreSQL (Supabase). This is intentional for first-time bring-up — do not "fix" the conditional. The committed `db.sqlite3` is the dev fallback DB.

### Custom user model is gated

`AUTH_USER_MODEL = 'users.User'` is **commented out** in `settings.py`. It must be enabled in the same commit that introduces the `users.User` model and its initial migration; flipping it after migrations exist will break the migration graph. The comment "於 Phase 1 TDD 實作 User Model 時啟用" marks this contract.

### Auth contract (Phase 1, partially implemented)

- DRF default: `IsAuthenticated` + `JWTAuthentication` (SimpleJWT). Anonymous endpoints must explicitly opt out (see `apps/core/views.py::health_check` for the pattern: `@permission_classes([AllowAny])`).
- Access token: 1h, refresh: 7d, rotation + blacklist enabled.
- Refresh token is delivered via httpOnly cookie (`REFRESH_TOKEN_COOKIE` in settings). The frontend Axios client uses `withCredentials: true` to make this work with CORS — both halves must stay aligned.
- Throttle defaults: `5/min` anon, `30/min` user.

### Frontend API client

`src/api/client.ts` reads `VITE_API_BASE_URL` (defaults via `.env.local` to `http://localhost:8000/api/v1`). 401 refresh-token interceptor is **not yet implemented** but is required by the auth contract — the comment in the file points to `.doc/taskflow-frontend.md §4.3`.

### App naming gotcha

`.doc/taskflow-backend.md §2` calls out that the calendar app must be named `calendar_events/`, not `calendar/`, because `calendar` shadows a Python stdlib module and breaks Django's app loading.

### Locale / timezone

`LANGUAGE_CODE = 'zh-hant'`, `TIME_ZONE = 'Asia/Taipei'`, `USE_TZ = True`. All datetimes should be stored UTC-aware; serializers should render in user's local timezone where it matters.

## Working with the spec docs

The `.doc/` files are extensive (`taskflow-backend.md` is ~60KB, `taskflow-database.md` ~30KB). Before implementing a non-trivial feature, read the relevant section rather than inferring from sparse skeleton code — most files in `apps/` are intentionally near-empty and will mislead you about intended structure. Cross-references in code comments (e.g. `§4.5`) point into these docs.
