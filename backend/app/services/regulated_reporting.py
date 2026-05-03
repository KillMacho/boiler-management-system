"""Regulated reporting service — generates XML reports per FNS/FSS/PFR schemas.

Uses Jinja2 templates in app/templates/reports/.
All dates formatted as ДД.ММ.ГГГГ (Russian regulatory requirement).
Numbers serialized as strings with two decimal places.

Note: XML structures are simplified models for diploma defence.
      For production: XSD-validate against current FNS schema versions.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.personnel import Employee, Position, Timesheet

logger = logging.getLogger("regulated_reporting")

# ── paths ─────────────────────────────────────────────────────────────────────

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "reports"
_REPORTS_DIR = Path("reports")

# ── Jinja2 env ────────────────────────────────────────────────────────────────

_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,   # XML — ручной контроль спецсимволов
    trim_blocks=True,
    lstrip_blocks=True,
)

# ── Organization constants (test values for diploma) ─────────────────────────

ORG_INN = "7700000001"
ORG_KPP = "770001001"
ORG_NAME = "ООО КТТ-Сервис"
ORG_FSS_REG = "7700-12345"
ORG_PF_REG = "087-123-456789"

SIGNER_LAST = "Директоров"
SIGNER_FIRST = "Директор"
SIGNER_MIDDLE = "Директорович"

# Tax rates
NDFL_RATE = Decimal("0.13")
PF_RATE = Decimal("0.22")
OMS_RATE = Decimal("0.051")
FSS_RATE = Decimal("0.029")
FSS_INJURY_RATE = Decimal("0.002")


# ── helpers ───────────────────────────────────────────────────────────────────

def _fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")

def _fmt_num(v) -> str:
    return f"{Decimal(str(v)):.2f}"

def _parse_quarter(period: str) -> tuple[int, int, date, date]:
    """'2026-Q1' → (year=2026, quarter=1, first_day, last_day)."""
    m = re.match(r"^(\d{4})-Q([1-4])$", period)
    if not m:
        raise ValueError(f"Invalid quarter period '{period}'. Expected YYYY-QN.")
    year, q = int(m.group(1)), int(m.group(2))
    month_start = (q - 1) * 3 + 1
    month_end = q * 3
    first = date(year, month_start, 1)
    import calendar
    last = date(year, month_end, calendar.monthrange(year, month_end)[1])
    return year, q, first, last

# Quarter → period_code used in FNS XML (21=Q1, 31=Q2, 33=Q3, 34=Q4/year)
_QUARTER_CODE = {1: "21", 2: "31", 3: "33", 4: "34"}


@dataclass
class ReportResult:
    report_type: str
    period: str
    filepath: str
    size_bytes: int


# ── DB data fetching ──────────────────────────────────────────────────────────

async def _fetch_employees_with_income(
    session: AsyncSession, first: date, last: date
) -> list[dict]:
    """Aggregate employee income and contributions for the period from timesheets."""
    ts_rows = await session.execute(
        select(Timesheet)
        .options(
            selectinload(Timesheet.employee).selectinload(Employee.position),
        )
        .where(Timesheet.date >= first, Timesheet.date <= last)
    )
    timesheets = list(ts_rows.scalars().all())

    agg: dict[int, dict[str, Any]] = {}
    for ts in timesheets:
        emp = ts.employee
        eid = ts.employee_id
        if eid not in agg:
            parts = [emp.last_name, emp.first_name]
            mid = emp.middle_name or ""
            base_salary = emp.position.base_salary if emp.position else Decimal("50000")
            agg[eid] = {
                "id": eid,
                "last_name": emp.last_name,
                "first_name": emp.first_name,
                "middle_name": mid,
                "inn_fl": f"77{eid:010d}"[:12],   # fake FL INN
                "snils": f"{eid:011d}"[:11],        # fake SNILS
                "income": Decimal("0"),
                "base_salary": base_salary,
                "hours": Decimal("0"),
            }
        hours = ts.hours_worked
        if ts.hours_type == "regular":
            hourly = agg[eid]["base_salary"] / Decimal("176")
            agg[eid]["income"] += hourly * hours
        elif ts.hours_type == "overtime":
            hourly = agg[eid]["base_salary"] / Decimal("176")
            agg[eid]["income"] += hourly * hours * Decimal("1.5")
        agg[eid]["hours"] += hours

    result = []
    for emp_data in agg.values():
        income = emp_data["income"]
        if income == 0:
            income = emp_data["base_salary"]  # fallback: use full salary
        ndfl = (income * NDFL_RATE).quantize(Decimal("0.01"))
        pf = (income * PF_RATE).quantize(Decimal("0.01"))
        oms = (income * OMS_RATE).quantize(Decimal("0.01"))
        fss = (income * FSS_RATE).quantize(Decimal("0.01"))
        fss_inj = (income * FSS_INJURY_RATE).quantize(Decimal("0.01"))
        result.append({
            **emp_data,
            "income": _fmt_num(income),
            "ndfl": _fmt_num(ndfl),
            "pf_contrib": _fmt_num(pf),
            "oms_contrib": _fmt_num(oms),
            "fss_contrib": _fmt_num(fss),
            "fss_injury": _fmt_num(fss_inj),
        })

    return result


def _stub_employees() -> list[dict]:
    """Fallback when no timesheet data exists — demo stub."""
    stubs = [
        ("Иванов", "Иван", "Иванович", "50000"),
        ("Петров", "Пётр", "Петрович", "60000"),
        ("Сидорова", "Анна", "Васильевна", "55000"),
    ]
    result = []
    for i, (ln, fn, mn, inc) in enumerate(stubs, start=1):
        income = Decimal(inc)
        result.append({
            "id": i,
            "last_name": ln, "first_name": fn, "middle_name": mn,
            "inn_fl": f"77{i:010d}"[:12],
            "snils": f"{i:011d}"[:11],
            "income": _fmt_num(income),
            "ndfl": _fmt_num((income * NDFL_RATE).quantize(Decimal("0.01"))),
            "pf_contrib": _fmt_num((income * PF_RATE).quantize(Decimal("0.01"))),
            "oms_contrib": _fmt_num((income * OMS_RATE).quantize(Decimal("0.01"))),
            "fss_contrib": _fmt_num((income * FSS_RATE).quantize(Decimal("0.01"))),
            "fss_injury": _fmt_num((income * FSS_INJURY_RATE).quantize(Decimal("0.01"))),
        })
    return result


# ── render + save ─────────────────────────────────────────────────────────────

def _render_and_save(template_name: str, context: dict, report_type: str, period: str) -> ReportResult:
    tmpl = _jinja.get_template(template_name)
    xml_content = tmpl.render(**context)

    out_dir = _REPORTS_DIR / report_type / period
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{report_type}_{period.replace('/', '-')}.xml"
    out_path.write_text(xml_content, encoding="utf-8")

    size = out_path.stat().st_size
    logger.info("generated %s %s → %s (%d bytes)", report_type, period, out_path, size)
    return ReportResult(
        report_type=report_type,
        period=period,
        filepath=str(out_path),
        size_bytes=size,
    )


def _base_context(year: int, period_code: str) -> dict:
    return {
        "inn": ORG_INN,
        "kpp": ORG_KPP,
        "org_name": ORG_NAME,
        "fss_reg_number": ORG_FSS_REG,
        "pf_reg_number": ORG_PF_REG,
        "signer_last": SIGNER_LAST,
        "signer_first": SIGNER_FIRST,
        "signer_middle": SIGNER_MIDDLE,
        "report_year": str(year),
        "period_code": period_code,
        "date_doc": _fmt_date(date.today()),
        "id_file": uuid.uuid4().hex[:16].upper(),
    }


# ── public API ────────────────────────────────────────────────────────────────

async def generate_6_ndfl(session: Optional[AsyncSession], period: str) -> ReportResult:
    """Generate 6-NDFL (КНД 1151100) for a quarter period like '2026-Q1'."""
    year, q, first, last = _parse_quarter(period)
    employees = (
        await _fetch_employees_with_income(session, first, last) if session else []
    ) or _stub_employees()

    total_income = sum(Decimal(e["income"]) for e in employees)
    total_ndfl = sum(Decimal(e["ndfl"]) for e in employees)

    ctx = _base_context(year, _QUARTER_CODE[q])
    ctx.update({
        "ndfl_accrued": _fmt_num(total_ndfl),
        "ndfl_withheld": _fmt_num(total_ndfl),
        "ndfl_transferred": _fmt_num(total_ndfl),
        "employees": employees,
    })
    return _render_and_save("6-ndfl-template.xml", ctx, "6-NDFL", period)


async def generate_rsv(session: Optional[AsyncSession], period: str) -> ReportResult:
    """Generate RSV (КНД 1151111) for a quarter period."""
    year, q, first, last = _parse_quarter(period)
    employees = (
        await _fetch_employees_with_income(session, first, last) if session else []
    ) or _stub_employees()

    total_income = sum(Decimal(e["income"]) for e in employees)
    ctx = _base_context(year, _QUARTER_CODE[q])
    ctx.update({
        "employee_count": len(employees),
        "total_income": _fmt_num(total_income),
        "pf_amount": _fmt_num((total_income * PF_RATE).quantize(Decimal("0.01"))),
        "oms_amount": _fmt_num((total_income * OMS_RATE).quantize(Decimal("0.01"))),
        "fss_amount": _fmt_num((total_income * FSS_RATE).quantize(Decimal("0.01"))),
        "employees": employees,
    })
    return _render_and_save("rsv-template.xml", ctx, "RSV", period)


async def generate_4_fss(session: Optional[AsyncSession], period: str) -> ReportResult:
    """Generate 4-FSS for a quarter period."""
    year, q, first, last = _parse_quarter(period)
    employees = (
        await _fetch_employees_with_income(session, first, last) if session else []
    ) or _stub_employees()

    total_income = sum(Decimal(e["income"]) for e in employees)
    ctx = _base_context(year, _QUARTER_CODE[q])
    ctx.update({
        "employee_count": len(employees),
        "fss_injury_amount": _fmt_num(
            (total_income * FSS_INJURY_RATE).quantize(Decimal("0.01"))
        ),
        "employees": employees,
    })
    return _render_and_save("4-fss-template.xml", ctx, "4-FSS", period)


async def generate_szv_stazh(session: Optional[AsyncSession], year: int) -> ReportResult:
    """Generate СЗВ-СТАЖ for a full calendar year."""
    period = str(year)
    first = date(year, 1, 1)
    last = date(year, 12, 31)

    employees = (
        await _fetch_employees_with_income(session, first, last) if session else []
    ) or _stub_employees()

    ctx = _base_context(year, "")
    ctx.update({"employees": employees})
    return _render_and_save("szv-stazh-template.xml", ctx, "SZV-STAZH", period)
