from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse
from .database import engine, Base

STATIC_DIR = Path(__file__).parent.parent / "static"
_index_html: str = ""
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _index_html
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        _index_html = index_path.read_text(encoding="utf-8")
    yield
    await engine.dispose()


app = FastAPI(
    title="Workshop Management ERP",
    description="Backend API for Spec R Workshop Management System",
    version="1.0.0",
    lifespan=lifespan,
)

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
    return {"status": "ok", "service": "workshop-management-api"}


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    if not _index_html:
        return HTMLResponse(content=f"<h1>Frontend not found</h1><p>STATIC_DIR={STATIC_DIR}, exists={STATIC_DIR.exists()}</p>")
    return HTMLResponse(content=_index_html)
