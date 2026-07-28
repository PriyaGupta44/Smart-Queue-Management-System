![Tests](https://github.com/PriyaGupta44/Smart-Queue-Management-System/actions/workflows/ci.yml/badge.svg)

# QueueFlow — Smart Queue Management System

A full-stack Flask application for managing a real-world service
queue: students join a virtual line, track their position and
estimated wait time live, pay a fee, and receive a printable receipt
— while admins manage the queue, search and page through waiting/
called students, and view a full student roster with history.

Built as a learning-focused portfolio project, developed session by
session with an emphasis on professional backend practices: clean
architecture, tested code, and real security considerations (CSRF,
rate limiting, secure cookies, IDOR protection) rather than just
getting features working.

📓 **[Read the full development log](DEVLOG.md)** — day-by-day
decisions, bugs found, and lessons learned while building this.

## Features

**For students**
- Registration, login/logout, "remember me," and a full password
  reset flow with real email delivery
- Join the queue and get a unique token
- Live status page — real position and an ETA computed from actual
  historical service times, updated via lightweight polling (no
  page reloads)
- Simulated fee payment with a printable receipt
- Full payment history

**For admins**
- Dashboard with searchable, paginated waiting/called queues
- Call next / mark completed, with status-transition guards against
  double-actions
- Full student roster, searchable, with per-student queue/payment
  history
- Payment records view

**Under the hood**
- CSRF protection on every state-changing form
- Rate limiting on login, registration, and password reset
- Secure, scoped cookies (HttpOnly, SameSite, environment-aware Secure)
- IDOR-safe queries — every user-scoped resource is filtered by
  ownership, not just by ID
- Role validation enforced at both the application and database level
- Branded error pages (400/403/404/429/500) and centralized logging
- Versioned database migrations (Flask-Migrate/Alembic)
- Full pytest suite, run automatically on every push via GitHub Actions

## Tech Stack

- **Backend:** Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login,
  Flask-WTF, Flask-Mail, Flask-Limiter
- **Database:** SQLite (development) / PostgreSQL (production-ready)
- **Testing:** pytest
- **Server:** gunicorn
- **CI:** GitHub Actions (tests + flake8 lint on every push)

## Screenshots

<!-- Add screenshots here — student dashboard, live queue status, admin dashboard, receipt view -->

## Getting Started

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env              # then fill in real values — see .env.example for setup notes

flask db upgrade                  # create the database schema
flask --app run.py seed-admin admin@example.com "Admin Name"   # create your first admin

flask run
```

Visit `http://127.0.0.1:5000`.

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest -v
flake8 .
```

## Project Structure

├── app/
│ ├── admin/ # Admin blueprint — dashboard, students, payments
│ ├── auth/ # Registration, login, password reset
│ ├── main/ # Public pages
│ ├── student/ # Queue, payments, live status
│ ├── models/ # Student, QueueEntry, Payment
│ ├── templates/
│ └── extensions.py # Shared extension instances (db, login_manager, etc.)
├── migrations/ # Alembic migration history
├── tests/ # pytest suite
├── .github/workflows/ # CI pipeline
├── config.py
├── run.py
└── DEPLOYMENT.md # Production deployment checklist

## Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for a full production checklist,
including database, environment variables, and known limitations.

## Roadmap
Ideas for a future v2 — not required for this project to be considered
complete, but documented for anyone building on it:

- QR-code-based queue joining
- Real payment gateway integration
- SMS alerts alongside email
- AI-based wait time prediction
- Analytics dashboard
- Multi-department support
- Appointment scheduling

## License

MIT — see [LICENSE](LICENSE).