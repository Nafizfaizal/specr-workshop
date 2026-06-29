import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    String, Boolean, Integer, Numeric, Date, DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(
        SAEnum("superadmin", "admin", "technician", "manager", name="user_role"),
        nullable=False,
        default="technician",
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(200), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_type: Mapped[str] = mapped_column(String(20), nullable=False, default="individual")
    trn: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    vehicles: Mapped[list["Vehicle"]] = relationship("Vehicle", back_populates="customer")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="customer")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="customer")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False)
    make: Mapped[str] = mapped_column(String(100), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    plate: Mapped[str] = mapped_column(String(50), nullable=True)
    vin: Mapped[str] = mapped_column(String(100), nullable=True)
    mileage: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="vehicles")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="vehicle")
    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="vehicle")


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="staff")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    staff_id: Mapped[str] = mapped_column(String(36), ForeignKey("staff.id"), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(
            "pending", "inprogress", "waitingparts", "qc", "ready",
            "delivered", "completed", "invoiced",
            name="job_status",
        ),
        nullable=False,
        default="pending",
    )
    priority: Mapped[str] = mapped_column(
        SAEnum("normal", "urgent", name="job_priority"),
        nullable=False,
        default="normal",
    )
    date_in: Mapped[date] = mapped_column(Date, nullable=False)
    date_out: Mapped[date] = mapped_column(Date, nullable=True)
    mileage_in: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=True)
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    completed_at: Mapped[date] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    customer: Mapped["Customer"] = relationship("Customer", back_populates="jobs")
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="jobs")
    staff: Mapped["Staff"] = relationship("Staff", back_populates="jobs")
    services: Mapped[list["JobService"]] = relationship(
        "JobService", back_populates="job", cascade="all, delete-orphan"
    )
    parts: Mapped[list["JobPart"]] = relationship(
        "JobPart", back_populates="job", cascade="all, delete-orphan"
    )
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="job", uselist=False)


class JobService(Base):
    __tablename__ = "job_services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="services")


class JobPart(Base):
    __tablename__ = "job_parts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    part_no: Mapped[str] = mapped_column(String(100), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="parts")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), unique=True, nullable=False)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    inv_num: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    date_issued: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("5.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    date_paid: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    job: Mapped["Job"] = relationship("Job", back_populates="invoice")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="invoices")
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="invoices")


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    vendor: Mapped[str] = mapped_column(String(200), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    part_no: Mapped[str] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=True)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    sell_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=Decimal("0"))
    reorder_qty: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=Decimal("0"))
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(200), nullable=True)
    trn: Mapped[str] = mapped_column(String(50), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    bills: Mapped[list["PurchaseBill"]] = relationship("PurchaseBill", back_populates="supplier")


class PurchaseBill(Base):
    __tablename__ = "purchase_bills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    supplier_id: Mapped[str] = mapped_column(String(36), ForeignKey("suppliers.id"), nullable=False)
    bill_no: Mapped[str] = mapped_column(String(100), nullable=True)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="bills")
    items: Mapped[list["PurchaseBillItem"]] = relationship(
        "PurchaseBillItem", back_populates="bill", cascade="all, delete-orphan"
    )


class PurchaseBillItem(Base):
    __tablename__ = "purchase_bill_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    bill_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("purchase_bills.id", ondelete="CASCADE"), nullable=False
    )
    part_name: Mapped[str] = mapped_column(String(200), nullable=False)
    part_no: Mapped[str] = mapped_column(String(100), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    bill: Mapped["PurchaseBill"] = relationship("PurchaseBill", back_populates="items")


class FixedCost(Base):
    __tablename__ = "fixed_costs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(
        SAEnum("monthly", "weekly", "quarterly", "yearly", "one-time", name="fc_frequency"),
        nullable=False,
        default="monthly",
    )
    next_due_date: Mapped[date] = mapped_column(Date, nullable=True)
    reminder_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    vendor: Mapped[str] = mapped_column(String(200), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_paid_date: Mapped[date] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    supplier_reminder_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)


class Estimate(Base):
    __tablename__ = "estimates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    staff_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("staff.id"), nullable=True)
    est_num: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    date_issued: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("draft", "sent", "approved", "rejected", "converted", name="est_status"),
        nullable=False, default="draft",
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    customer: Mapped["Customer"] = relationship("Customer")
    vehicle: Mapped["Vehicle"] = relationship("Vehicle")
    staff: Mapped[Optional["Staff"]] = relationship("Staff")
    services: Mapped[list["EstimateService"]] = relationship(
        "EstimateService", back_populates="estimate", cascade="all, delete-orphan"
    )
    parts: Mapped[list["EstimatePart"]] = relationship(
        "EstimatePart", back_populates="estimate", cascade="all, delete-orphan"
    )


class EstimateService(Base):
    __tablename__ = "estimate_services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    estimate_id: Mapped[str] = mapped_column(String(36), ForeignKey("estimates.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    estimate: Mapped["Estimate"] = relationship("Estimate", back_populates="services")


class EstimatePart(Base):
    __tablename__ = "estimate_parts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    estimate_id: Mapped[str] = mapped_column(String(36), ForeignKey("estimates.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    part_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    estimate: Mapped["Estimate"] = relationship("Estimate", back_populates="parts")
