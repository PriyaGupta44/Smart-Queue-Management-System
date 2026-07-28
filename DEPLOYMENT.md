# Deployment Checklist

This app is ready to deploy behind gunicorn. Before deploying, work
through this list in order.

## 1. Choose a database

SQLite (the local default) works fine on a traditional VPS with
persistent disk. **It will silently reset to empty on every deploy**
on any platform with an ephemeral filesystem (Heroku, Render, Railway,
Fly.io, most container-based hosts). If you're deploying to one of
those, set up a managed PostgreSQL database and point `DATABASE_URL`
at it instead — `psycopg2-binary` is already in `requirements.txt` to
support this.


## 2. Set required environment variables

| Variable | Required? | Notes |
|---|---|---|
| `FLASK_CONFIG` | Yes | Set to `production` |
| `SECRET_KEY` | Yes | The app refuses to start without this in production (Day 18). Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Recommended | Postgres URI if the host has an ephemeral filesystem (see above) |
| `MAIL_USERNAME` / `MAIL_PASSWORD` / `MAIL_DEFAULT_SENDER` | Yes, if password reset is used | Gmail App Password — see `.env.example` for setup steps |
| `RATELIMIT_STORAGE_URI` | Recommended for multi-worker | Defaults to in-memory, which means each gunicorn worker counts rate limits *separately*. With `--workers 3`, a "10 per minute" limit effectively becomes ~30 per minute across all workers. A shared backend like Redis fixes this — not strictly required to launch, but worth knowing about |
| `SESSION_COOKIE_SECURE` | Automatic | `ProductionConfig` forces this `True` regardless of the env var — only relevant if serving over HTTP for some reason (not recommended) |

## 3. Run database migrations

The `Procfile`'s `release: flask db upgrade` line handles this
automatically on platforms with a release phase. If your host doesn't
support one, run it manually after each deploy:

```bash
flask db upgrade
```

## 4. Create your first admin account

```bash
flask --app run.py seed-admin admin@yourschool.edu "Admin Name"
```

## 5. Start the server

```bash
gunicorn run:app --workers 3 --timeout 60 --bind 0.0.0.0:$PORT
```

(The `Procfile` already specifies this — most platforms read it
automatically and you won't need to run this by hand.)

## 6. Verify after deploying

- [ ] Visiting the site loads the homepage over HTTPS
- [ ] `DEBUG` is off — trigger a deliberate error and confirm you see the branded 500 page (Day 18), not a stack trace
- [ ] Registering and logging in both work
- [ ] Password reset emails actually arrive
- [ ] Logs are visible in your host's log viewer (confirms the Day 23 stdout logging change is working)
- [ ] The admin dashboard is reachable and shows real data after seeding an admin

## Known limitations, honestly stated

- Rate limiting uses in-memory storage by default — correct on a
  single worker, approximate (limits effectively multiply by worker
  count) with more than one, unless `RATELIMIT_STORAGE_URI` points at
  Redis.
- SQLite is not suitable for any host with an ephemeral filesystem —
  see section 1.
- There is currently no CI pipeline verifying tests pass before a
  deploy goes out (planned for Day 24).