from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from .database import engine, Base
from .routers import (
    auth,
    customers,
    vehicles,
    staff,
    jobs,
    invoices,
    expenses,
    inventory,
    suppliers,
    purchase_bills,
    fixed_costs,
    reports,
    settings,
    users,
)

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Additive migrations for columns added after initial deploy
        from sqlalchemy import text
        await conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS notes TEXT"))
        await conn.execute(text("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50)"))
        await conn.execute(text("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS date_paid DATE"))
        await conn.execute(text("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS tax_rate NUMERIC(5,2) NOT NULL DEFAULT 5.00"))
        await conn.execute(text("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS tax_amount NUMERIC(10,2) NOT NULL DEFAULT 0.00"))
        await conn.execute(text("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS grand_total NUMERIC(10,2) NOT NULL DEFAULT 0.00"))
        await conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS customer_type VARCHAR(20) NOT NULL DEFAULT 'individual'"))
        await conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS trn VARCHAR(50)"))
    yield
    await engine.dispose()


app = FastAPI(title="Workshop Management ERP", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(customers.router, prefix=API_PREFIX)
app.include_router(vehicles.router, prefix=API_PREFIX)
app.include_router(staff.router, prefix=API_PREFIX)
app.include_router(jobs.router, prefix=API_PREFIX)
app.include_router(invoices.router, prefix=API_PREFIX)
app.include_router(expenses.router, prefix=API_PREFIX)
app.include_router(inventory.router, prefix=API_PREFIX)
app.include_router(suppliers.router, prefix=API_PREFIX)
app.include_router(purchase_bills.router, prefix=API_PREFIX)
app.include_router(fixed_costs.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(settings.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(content=index.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>App loading...</h1>")
