from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, EmailStr


# ─── User ────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    username: str
    name: str
    role: str = "technician"
    active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    new_password: str


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Customer ────────────────────────────────────────────────────────────────

class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


# ─── Vehicle ─────────────────────────────────────────────────────────────────

class VehicleBase(BaseModel):
    customer_id: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    plate: Optional[str] = None
    vin: Optional[str] = None
    mileage: Optional[int] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    customer_id: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    plate: Optional[str] = None
    vin: Optional[str] = None
    mileage: Optional[int] = None


class VehicleResponse(VehicleBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    customer: Optional[CustomerResponse] = None


# ─── Staff ───────────────────────────────────────────────────────────────────

class StaffBase(BaseModel):
    name: str
    role: Optional[str] = None
    phone: Optional[str] = None


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None


class StaffResponse(StaffBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


# ─── JobService ──────────────────────────────────────────────────────────────

class JobServiceBase(BaseModel):
    description: str
    department: Optional[str] = None
    rate: Decimal


class JobServiceCreate(JobServiceBase):
    pass


class JobServiceResponse(JobServiceBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_id: str


# ─── JobPart ─────────────────────────────────────────────────────────────────

class JobPartBase(BaseModel):
    description: str
    part_no: Optional[str] = None
    qty: Decimal
    rate: Decimal


class JobPartCreate(JobPartBase):
    pass


class JobPartResponse(JobPartBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    job_id: str


# ─── Job ─────────────────────────────────────────────────────────────────────

class JobBase(BaseModel):
    customer_id: str
    vehicle_id: str
    staff_id: Optional[str] = None
    department: Optional[str] = None
    status: str = "pending"
    priority: str = "normal"
    date_in: date
    date_out: Optional[date] = None
    mileage_in: Optional[int] = None
    notes: Optional[str] = None
    diagnosis: Optional[str] = None
    discount: Decimal = Decimal("0")


class JobCreate(JobBase):
    services: List[JobServiceCreate] = []
    parts: List[JobPartCreate] = []


class JobUpdate(BaseModel):
    customer_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    staff_id: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    date_in: Optional[date] = None
    date_out: Optional[date] = None
    mileage_in: Optional[int] = None
    notes: Optional[str] = None
    diagnosis: Optional[str] = None
    discount: Optional[Decimal] = None
    services: Optional[List[JobServiceCreate]] = None
    parts: Optional[List[JobPartCreate]] = None


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    completed_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    services: List[JobServiceResponse] = []
    parts: List[JobPartResponse] = []
    customer: Optional[CustomerResponse] = None
    vehicle: Optional[VehicleResponse] = None
    staff: Optional[StaffResponse] = None


# ─── Invoice ─────────────────────────────────────────────────────────────────

class InvoiceBase(BaseModel):
    job_id: str
    customer_id: str
    vehicle_id: str
    inv_num: str
    date_issued: date
    subtotal: Decimal
    tax_rate: Decimal = Decimal("5.00")
    tax_amount: Decimal = Decimal("0.00")
    grand_total: Decimal = Decimal("0.00")
    paid: bool = False
    payment_method: Optional[str] = None
    date_paid: Optional[date] = None


class InvoiceCreate(BaseModel):
    job_id: str
    date_issued: Optional[date] = None


class InvoiceResponse(InvoiceBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    job: Optional[JobResponse] = None
    customer: Optional[CustomerResponse] = None
    vehicle: Optional[VehicleResponse] = None


# ─── Expense ─────────────────────────────────────────────────────────────────

class ExpenseBase(BaseModel):
    date: date
    category: Optional[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None
    amount: Decimal


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    date: Optional[date] = None
    category: Optional[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None
    amount: Optional[Decimal] = None


class ExpenseResponse(ExpenseBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


# ─── Inventory ───────────────────────────────────────────────────────────────

class InventoryBase(BaseModel):
    name: str
    part_no: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Decimal = Decimal("0")
    sell_price: Decimal = Decimal("0")
    qty: Decimal = Decimal("0")
    reorder_qty: Decimal = Decimal("0")
    notes: Optional[str] = None


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    name: Optional[str] = None
    part_no: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    qty: Optional[Decimal] = None
    reorder_qty: Optional[Decimal] = None
    notes: Optional[str] = None


class InventoryAdjust(BaseModel):
    type: str  # add | remove | set
    qty: float
    reason: Optional[str] = None


class StockAdjust(BaseModel):
    type: Literal["add", "remove", "set"]
    qty: float
    reason: str = ""


class InventoryResponse(InventoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


# ─── Supplier ────────────────────────────────────────────────────────────────

class SupplierBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    trn: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    trn: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SupplierResponse(SupplierBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


# ─── PurchaseBillItem ────────────────────────────────────────────────────────

class PurchaseBillItemBase(BaseModel):
    part_name: str
    part_no: Optional[str] = None
    qty: Decimal
    cost_price: Decimal


class PurchaseBillItemCreate(PurchaseBillItemBase):
    pass


class PurchaseBillItemResponse(PurchaseBillItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    bill_id: str


# ─── PurchaseBill ────────────────────────────────────────────────────────────

class PurchaseBillBase(BaseModel):
    supplier_id: str
    bill_no: Optional[str] = None
    bill_date: date
    due_date: Optional[date] = None
    notes: Optional[str] = None
    paid: bool = False


class PurchaseBillCreate(PurchaseBillBase):
    items: List[PurchaseBillItemCreate] = []


class PurchaseBillUpdate(BaseModel):
    supplier_id: Optional[str] = None
    bill_no: Optional[str] = None
    bill_date: Optional[date] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    paid: Optional[bool] = None
    items: Optional[List[PurchaseBillItemCreate]] = None


class PurchaseBillResponse(PurchaseBillBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    supplier: Optional[SupplierResponse] = None
    items: List[PurchaseBillItemResponse] = []


# ─── FixedCost ───────────────────────────────────────────────────────────────

class FixedCostBase(BaseModel):
    name: str
    category: Optional[str] = None
    amount: Decimal
    frequency: str = "monthly"
    next_due_date: Optional[date] = None
    reminder_days: int = 7
    vendor: Optional[str] = None
    notes: Optional[str] = None
    active: bool = True


class FixedCostCreate(FixedCostBase):
    pass


class FixedCostUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[Decimal] = None
    frequency: Optional[str] = None
    next_due_date: Optional[date] = None
    reminder_days: Optional[int] = None
    vendor: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class FixedCostResponse(FixedCostBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    last_paid_date: Optional[date] = None
    created_at: datetime


# ─── AppSettings ─────────────────────────────────────────────────────────────

class AppSettingsBase(BaseModel):
    supplier_reminder_days: int = 7


class AppSettingsUpdate(BaseModel):
    supplier_reminder_days: Optional[int] = None


class AppSettingsResponse(AppSettingsBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ─── Dashboard ───────────────────────────────────────────────────────────────

class PaymentAlert(BaseModel):
    type: str  # "bill" | "fixed_cost"
    id: str
    name: str
    amount: Decimal
    due_date: Optional[date]
    overdue: bool
    days_until_due: Optional[int]


class DashboardStats(BaseModel):
    total_revenue: Decimal
    revenue_today: Decimal
    revenue_this_month: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    open_jobs: int
    urgent_jobs: int
    overdue_jobs: List[dict]
    ready_jobs: int
    waiting_parts_jobs: int
    completed_this_month: int
    total_completed: int
    unpaid_invoices_amount: Decimal
    unpaid_invoices_count: int
    supplier_due_amount: Decimal
    supplier_overdue_count: int
    fc_due_amount: Decimal
    fc_overdue_count: int
    payment_alerts: List[PaymentAlert]
    revenue_by_month: dict
    expenses_by_month: dict
    dept_revenue: dict
