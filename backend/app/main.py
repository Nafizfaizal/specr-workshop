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
_frontend_html: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _frontend_html
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    index_path = STATIC_DIR / "index.html"
    try:
        _frontend_html = index_path.read_text(encoding="utf-8")
    except Exception:
        pass
    yield
    await engine.dispose()


app = FastAPI(
    title="Workshop Management ERP",
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
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    if _frontend_html:
        return HTMLResponse(content=_frontend_html)
    return HTMLResponse(content="<h1>Loading...</h1>")
