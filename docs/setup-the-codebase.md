# Setup the codebase

This guide explains **how this backend project is set up** in plain language.
You do not need to be a Django expert to follow it.

By the end, you should understand:

- what this repo is
- what the main folders/files do
- how to install and run the project on your machine

For APIs and curl commands, see:

- [Auth docs](./auth/README.md) (signup, login, health)
- [Flipbook docs](./flipbook/README.md) (coming later)

---

## What is this project?

**RD Flip Backend** (`rd-flip-be`) is the **server side** of the RD Flip product.

- The **frontend** is what users see and click.
- This **backend** stores data and serves APIs.

---

## What you need before starting

1. **Python 3.10+**
2. **Poetry** — installs packages and manages the project environment
3. **PostgreSQL** — database for users and flipbooks

Optional: TablePlus, DBeaver, or pgAdmin to view tables.

---

## Folder structure

```text
rd-flip-be/
├── docs/
│   ├── setup-the-codebase.md   ← this file (setup only)
│   ├── auth/                   ← auth API docs
│   │   ├── README.md
│   │   ├── signup.md
│   │   └── login.md
│   └── flipbook/               ← flipbook API docs (later)
├── apps/
│   ├── auth/                   ← auth feature code
│   │   ├── apps.py
│   │   ├── helpers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   └── migrations/
│   └── flipbooks/              ← flipbook feature code (placeholder)
├── rd_flip_be/                 ← main project entry point
│   ├── settings.py
│   ├── urls.py
│   ├── models.py
│   ├── wsgi.py / asgi.py
│   ├── apps.py
│   ├── admin.py
│   └── migrations/
├── manage.py
├── pyproject.toml
├── poetry.lock
├── .env
├── .gitignore
└── README.md
```

### `rd_flip_be/` — entry point

| File | Meaning |
|------|---------|
| `settings.py` | Database, apps, JWT, CORS, etc. |
| `urls.py` | Main URL map |
| `models.py` | User, Flipbook, FlipbookPage |
| `wsgi.py` / `asgi.py` | How the server starts the app |
| `apps.py` | Registers this package as a Django app |
| `admin.py` | Django admin (empty for now) |
| `migrations/` | Database change history |

### `apps/auth/` — auth feature code

| File | Meaning |
|------|---------|
| `helpers.py` | Shared helpers (phone `+91` normalize) |
| `urls.py` | `health/`, `signup/`, `login/` |
| `views.py` | API handlers |
| `serializers.py` | Request validation |
| `apps.py` | App config (`label = user_auth`) |

### `apps/flipbooks/`

Placeholder for flipbook feature code.

**Models are not inside feature apps.** They live in `rd_flip_be/models.py`.

### Root files

| File | Meaning |
|------|---------|
| `manage.py` | Django commands (migrate, runserver, …) |
| `pyproject.toml` | Project dependencies |
| `poetry.lock` | Locked package versions |
| `.env` | Local secrets and DB settings |

---

## Understanding `.env`

Django reads `.env` via `django-environ` in `rd_flip_be/settings.py`.

| Key | Meaning |
|-----|---------|
| `SECRET_KEY` | Django secret (change for real deployments) |
| `DEBUG` | `True` locally; `False` in production |
| `ALLOWED_HOSTS` | Allowed hostnames (e.g. `localhost,127.0.0.1`) |
| `DATABASE_NAME` | Postgres database name |
| `DATABASE_USER` | DB username |
| `DATABASE_PASSWORD` | DB password |
| `DATABASE_HOST` | DB host (`localhost` or Railway host) |
| `DATABASE_PORT` | Public port (Railway proxy port may not be `5432`) |
| `CORS_ALLOW_ALL_ORIGINS` | Allow frontend origins in development |
| `JWT_ACCESS_MINUTES` | Access token lifetime |
| `JWT_REFRESH_DAYS` | Refresh token lifetime |

Do **not** commit real production secrets. `.env` is gitignored.

---

## Packages (`pyproject.toml`)

| Package | Why |
|---------|-----|
| Django | Web framework |
| djangorestframework | APIs |
| django-environ | Read `.env` |
| psycopg2-binary | Postgres driver |
| django-cors-headers | Frontend CORS |
| djangorestframework-simplejwt | JWT auth |
| pillow | Images (flipbook pages later) |

---

## Step-by-step setup

### 1) Enter the project folder

```bash
cd /path/to/rd-flip-be
```

### 2) Install dependencies

```bash
poetry install
```

### 3) Activate Poetry env

```bash
poetry shell
```

Or run commands with:

```bash
poetry run python manage.py ...
```

### 4) Configure Postgres in `.env`

Set `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT` to match your database (local or Railway).

### 5) Run migrations

```bash
python manage.py migrate
```

### 6) Start the server

```bash
python manage.py runserver
```

Server: `http://127.0.0.1:8000/`

### 7) Confirm it works

```bash
curl http://127.0.0.1:8000/api/auth/health/
```

Expected: `{"status": "ok"}`

API usage (signup/login): see [docs/auth/](./auth/README.md)

---

## How a request flows

1. Request hits Django
2. `rd_flip_be/urls.py` routes `api/auth/` to `apps.auth.urls`
3. `apps/auth/urls.py` maps the path to a view
4. View (+ serializer) returns JSON

---

## Common first-time problems

1. **DB role/user missing** — create the Postgres user, or fix `.env`
2. **Poetry not found** — install Poetry, reopen terminal
3. **Wrong Python** — need 3.10+
4. **Port 8000 busy** — `python manage.py runserver 8001`
5. **Railway DB** — use the **public proxy port**, not only internal `5432`

---

## Command cheat sheet

```bash
poetry install
poetry shell
python manage.py migrate
python manage.py runserver
python manage.py makemigrations
python manage.py check
python manage.py createsuperuser
```

---

## Summary

- This repo is the RD Flip **backend**
- `rd_flip_be/` = entry point (settings, urls, models)
- `apps/auth` / `apps/flipbooks` = feature code
- Setup this file only; APIs live under `docs/auth/` and `docs/flipbook/`
