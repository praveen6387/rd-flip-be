# RD Flip Backend

Django + DRF API for auth and flipbook operations.

Entry point package: `rd_flip_be/`

## Quick start

```bash
poetry install
poetry shell
# edit .env (DATABASE_NAME / USER / PASSWORD / HOST / PORT)
python manage.py migrate
python manage.py runserver
```

## Docs

| Link | Purpose |
|------|---------|
| [Docs index](./docs/README.md) | All guides |
| [Setup](./docs/setup-the-codebase.md) | Codebase setup only |
| [Auth](./docs/auth/README.md) | Auth APIs |
| [Signup](./docs/auth/signup.md) | Signup + curl |
| [Login](./docs/auth/login.md) | Login + curl |
| [Refresh](./docs/auth/refresh.md) | Refresh token + frontend flow |
| [Flipbook](./docs/flipbook/README.md) | Flipbook APIs |
| [Flipbook · Create](./docs/flipbook/create.md) | Create flipbook + curl |
| [Flipbook · List](./docs/flipbook/list.md) | List flipbooks + curl |
