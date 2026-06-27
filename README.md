# Workshop Management ERP — Spec R

Full-stack ERP system for automotive workshop management. FastAPI + PostgreSQL backend.

---

## Local Development with Docker Compose

### Prerequisites
- Docker Desktop installed and running

### Start

```bash
cd /path/to/workshop-management-app
docker compose up --build
```

The API will be available at **http://localhost:8000**

Interactive API docs: **http://localhost:8000/docs**

### Stop

```bash
docker compose down
```

To also delete the database volume:

```bash
docker compose down -v
```

---

## Manual Setup (without Docker)

### Prerequisites
- Python 3.12
- PostgreSQL 16 running locally

### Steps

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set DATABASE_URL to point to your local Postgres instance
```

Create the database:

```sql
CREATE USER specr WITH PASSWORD 'specr_dev_password';
CREATE DATABASE specr_db OWNER specr;
```

Run the server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Tables are created automatically on first startup via SQLAlchemy metadata.

---

## Default Credentials

On first launch, if no users exist, the system seeds:

| Username | Password  | Role       |
|----------|-----------|------------|
| admin    | admin123  | superadmin |

**Change this password immediately after first login.**

---

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

All endpoints (except `POST /api/auth/login`) require a Bearer token.

### Authentication

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

Response includes `access_token`. Pass it as:

```
Authorization: Bearer <access_token>
```

---

## Railway Deployment

1. Create a new Railway project
2. Add a **PostgreSQL** plugin — Railway auto-injects `DATABASE_URL`
3. Connect this GitHub repo, set the **Root Directory** to `backend`
4. Set environment variables in Railway dashboard:
   - `SECRET_KEY` — a long random string (use `openssl rand -hex 32`)
   - `ALGORITHM` — `HS256`
   - `ACCESS_TOKEN_EXPIRE_MINUTES` — `1440`
5. Railway uses `railway.json` to configure the build and start command

### Render Deployment

1. Create a new **Web Service** pointing to this repo
2. Set **Root Directory** to `backend`
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add a **PostgreSQL** database and link it — set `DATABASE_URL` in env vars
6. Add `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`

---

## Project Structure

```
workshop-management-app/
├── docker-compose.yml
├── README.md
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── railway.json
    ├── .env.example
    └── app/
        ├── main.py           # FastAPI app + lifespan
        ├── config.py         # Pydantic settings
        ├── database.py       # Async SQLAlchemy engine
        ├── models.py         # ORM models
        ├── schemas.py        # Pydantic v2 schemas
        ├── auth.py           # JWT + password utilities
        └── routers/
            ├── auth.py
            ├── customers.py
            ├── vehicles.py
            ├── staff.py
            ├── jobs.py
            ├── invoices.py
            ├── expenses.py
            ├── inventory.py
            ├── suppliers.py
            ├── purchase_bills.py
            ├── fixed_costs.py
            ├── reports.py
            ├── settings.py
            └── users.py
```

---

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/login | Login (JSON) |
| GET | /api/auth/me | Current user |
| PUT | /api/auth/me/password | Change own password |
| GET/POST | /api/customers | Customers CRUD |
| GET/POST | /api/vehicles | Vehicles CRUD |
| GET/POST | /api/jobs | Jobs CRUD |
| POST | /api/jobs/{id}/invoice | Generate invoice from job |
| GET/POST | /api/invoices | Invoices |
| PUT | /api/invoices/{id}/mark-paid | Mark invoice paid |
| GET/POST | /api/inventory | Inventory CRUD |
| POST | /api/inventory/{id}/adjust | Stock adjustment |
| GET/POST | /api/purchase-bills | Purchase bills |
| GET/POST | /api/fixed-costs | Fixed costs |
| PUT | /api/fixed-costs/{id}/mark-paid | Mark paid + advance due date |
| GET | /api/reports/dashboard | Dashboard stats |
| GET | /api/reports/tax | Tax/VAT report |
| GET | /api/reports/profitability | P&L report |
| GET | /api/reports/inventory-report | Inventory with low stock |
| GET | /api/reports/job-duration | Job turnaround times |
| GET/PUT | /api/settings | App settings |
| GET/POST | /api/users | User management (superadmin) |
