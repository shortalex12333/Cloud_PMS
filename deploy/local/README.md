# `deploy/local/` — local Docker stack environment

This directory holds **untracked** `.env` files that `docker-compose.yml` reads via
the `env_file:` directive. Nothing in `deploy/local/` with an `.env` suffix is
ever committed to git (`.env` and `.env.*` are in the repo `.gitignore`).

Two files live here:

| File | Scope | Contains |
|---|---|---|
| `.env` | Backend API + all Python workers | Service keys, JWT secrets, DB DSNs, OpenAI/Azure keys, worker knobs, feature flags |
| `.env.web` | Frontend (Next.js) | Public Supabase URL/anon key, public API URL, yacht salt |

Corresponding **templates** (tracked) in this directory:

- `.env.template` — every key the backend/workers expect, with empty values and inline comments
- `.env.web.template` — every key the frontend expects, with empty values

## First-time local setup

```bash
cp deploy/local/.env.template deploy/local/.env
cp deploy/local/.env.web.template deploy/local/.env.web
# Fill in real values (ask the repo owner for the secret set)
make docker    # starts the full stack; see Makefile
```

## What NOT to do

- Don't commit `deploy/local/.env` or `deploy/local/.env.web` — they contain secrets.
- Don't rename this directory — it's referenced by `docker-compose.yml`.
- Don't put secret values in the `*.template` files — templates are tracked and should contain only key names + comments.

## Why `deploy/local/` exists (vs root `.env`)

The root `.env` (also gitignored) is used by tooling that expects a flat `.env` in the project root. `deploy/local/` is the docker-compose-specific location that keeps local-stack config together with `docker-compose.yml`.
