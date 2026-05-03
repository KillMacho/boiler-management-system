"""Gather period data from DB and format it for 1C transmission.

Collects acts, material movements, timesheets for a YYYY-MM period,
builds accounting transactions by template, and calls OneCClient methods.
"""
from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.personnel import Employee, Position, Timesheet
from app.models.requests import Act, WorkOrder
from app.models.warehouse import Material, MaterialMovement
from app.services.onec_client import onec_client

logger = logging.getLogger("onec_period_service")


@dataclass
class PeriodSendResult:
    period: str
    acts_sent: int = 0
    materials_sent: int = 0
    transactions_sent: int = 0
    timesheet_rows_sent: int = 0
    acts_response: dict = field(default_factory=dict)
    materials_response: dict = field(default_factory=dict)
    transactions_response: dict = field(default_factory=dict)
    timesheet_response: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _parse_period(period: str) -> tuple[date, date]:
    """'YYYY-MM' → (first_day, last_day)."""
    year, month = int(period[:4]), int(period[5:7])
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return first, last


# ── Acts ──────────────────────────────────────────────────────────────────────

async def _gather_acts(session: AsyncSession, first: date, last: date) -> list[dict]:
    """Load all Acts generated in [first, last] with related WorkOrder/Boiler data."""
    rows = await session.execute(
        select(Act)
        .join(Act.work_order)
        .options(
            selectinload(Act.work_order).selectinload(WorkOrder.brigade),
            selectinload(Act.work_order).selectinload(WorkOrder.request),
            selectinload(Act.work_order).selectinload(WorkOrder.material_movements)
            .selectinload(MaterialMovement.material),
        )
        .where(
            func.cast(Act.generated_at, __import__("sqlalchemy").Date) >= first,
            func.cast(Act.generated_at, __import__("sqlalchemy").Date) <= last,
        )
    )
    acts = list(rows.scalars().all())

    result = []
    for act in acts:
        wo = act.work_order
        boiler = wo.request.boiler if wo and wo.request else None
        brigade = wo.brigade if wo else None

        materials_list = []
        if wo:
            for mv in wo.material_movements:
                if mv.movement_type == "outcome":
                    materials_list.append({
                        "номенклатура": mv.material.name if mv.material else "?",
                        "количество": float(mv.quantity),
                        "цена": float(mv.material.price) if mv.material else 0.0,
                    })

        result.append({
            "номер_акта": act.number,
            "дата": act.generated_at.date().isoformat(),
            "котельная_id": boiler.id if boiler else 0,
            "котельная_наименование": boiler.name if boiler else "Неизвестная котельная",
            "бригада": brigade.name if brigade else "Неизвестная бригада",
            "сумма": float(act.total_amount),
            "материалы": materials_list,
        })

    return result


# ── Material movements ────────────────────────────────────────────────────────

async def _gather_material_movements(
    session: AsyncSession, first: date, last: date
) -> list[dict]:
    """Load all outcome material movements for the period."""
    rows = await session.execute(
        select(MaterialMovement)
        .options(
            selectinload(MaterialMovement.material),
            selectinload(MaterialMovement.work_order)
            .selectinload(WorkOrder.request),
        )
        .where(
            MaterialMovement.movement_type == "outcome",
            func.cast(MaterialMovement.created_at, __import__("sqlalchemy").Date) >= first,
            func.cast(MaterialMovement.created_at, __import__("sqlalchemy").Date) <= last,
        )
    )
    movements = list(rows.scalars().all())

    result = []
    for mv in movements:
        wo = mv.work_order
        boiler_name = (
            wo.request.boiler.name
            if wo and wo.request and wo.request.boiler
            else "Неизвестная котельная"
        )
        work_order_number = (
            wo.request.number if wo and wo.request else "?"
        )
        result.append({
            "тип_операции": "списание",
            "дата": mv.created_at.date().isoformat(),
            "номенклатура": mv.material.name if mv.material else "?",
            "количество": float(mv.quantity),
            "сумма": float(mv.quantity * mv.material.price) if mv.material else 0.0,
            "наряд_номер": work_order_number,
            "котельная_наименование": boiler_name,
        })

    return result


# ── Timesheet ─────────────────────────────────────────────────────────────────

async def _gather_timesheet(
    session: AsyncSession, first: date, last: date
) -> list[dict]:
    """Aggregate timesheet rows per employee for the period."""
    rows = await session.execute(
        select(Timesheet)
        .options(
            selectinload(Timesheet.employee).selectinload(Employee.position),
        )
        .where(
            Timesheet.date >= first,
            Timesheet.date <= last,
        )
    )
    timesheets = list(rows.scalars().all())

    # Aggregate by employee
    agg: dict[int, dict] = {}
    for ts in timesheets:
        emp = ts.employee
        emp_id = ts.employee_id
        if emp_id not in agg:
            fio = f"{emp.last_name} {emp.first_name[0]}.{(emp.middle_name[0] + '.') if emp.middle_name else ''}" if emp else f"Сотрудник #{emp_id}"
            agg[emp_id] = {
                "сотрудник_id": emp_id,
                "сотрудник_фио": fio,
                "обычные_часы": 0.0,
                "сверхурочные": 0.0,
                "отпуск": 0.0,
                "больничный": 0.0,
            }
        hours = float(ts.hours_worked)
        if ts.hours_type == "overtime":
            agg[emp_id]["сверхурочные"] += hours
        elif ts.hours_type == "vacation":
            agg[emp_id]["отпуск"] += hours
        elif ts.hours_type == "sick":
            agg[emp_id]["больничный"] += hours
        else:
            agg[emp_id]["обычные_часы"] += hours

    return list(agg.values())


# ── Accounting transactions ───────────────────────────────────────────────────

def _build_transactions(
    period: str,
    acts: list[dict],
    movements: list[dict],
) -> list[dict]:
    """Generate standard accounting entries from acts and material movements.

    Templates (simplified 1C Accounting model):
      1. Material write-off:    Dt 20 (Основное пр-во)  Kt 10 (Материалы)
      2. Revenue recognition:   Dt 62 (Покупатели)      Kt 90.01 (Выручка)
      3. COGS write-off:        Dt 90.02 (Себестоимость) Kt 20
    """
    last_day = f"{period}-{calendar.monthrange(int(period[:4]), int(period[5:7]))[1]:02d}"
    entries = []

    # 1. Material write-offs
    for mv in movements:
        if mv["сумма"] > 0:
            entries.append({
                "дата": mv["дата"],
                "дебет_счёт": "20",
                "кредит_счёт": "10",
                "сумма": mv["сумма"],
                "содержание": f"Списание материалов на {mv['котельная_наименование']}",
                "субконто_дт": mv["котельная_наименование"],
                "субконто_кт": mv["номенклатура"],
            })

    # 2 & 3. Revenue and COGS per act
    for act in acts:
        if act["сумма"] > 0:
            entries.append({
                "дата": act["дата"],
                "дебет_счёт": "62",
                "кредит_счёт": "90.01",
                "сумма": act["сумма"],
                "содержание": f"Реализация работ: {act['номер_акта']}",
                "субконто_дт": act["котельная_наименование"],
                "субконто_кт": None,
            })
            # COGS = sum of materials in act
            cogs = sum(m["количество"] * m["цена"] for m in act.get("материалы", []))
            if cogs > 0:
                entries.append({
                    "дата": last_day,
                    "дебет_счёт": "90.02",
                    "кредит_счёт": "20",
                    "сумма": round(cogs, 2),
                    "содержание": f"Себестоимость работ: {act['номер_акта']}",
                    "субконто_дт": None,
                    "субконто_кт": act["котельная_наименование"],
                })

    return entries


# ── Main orchestrator ─────────────────────────────────────────────────────────

async def send_period_to_onec(
    session: AsyncSession,
    period: str,
) -> PeriodSendResult:
    """Gather all period data from DB and sequentially send to 1C mock.

    Order: send_acts → send_materials → send_transactions → send_timesheet.
    Errors are captured per step and included in result (partial success allowed).
    """
    result = PeriodSendResult(period=period)
    first, last = _parse_period(period)

    # 1. Acts
    acts = await _gather_acts(session, first, last)
    result.acts_sent = len(acts)
    try:
        result.acts_response = await onec_client.send_acts(period, acts)
    except Exception as exc:
        logger.error("send_acts failed: %s", exc)
        result.errors.append(f"acts: {exc}")

    # 2. Material movements
    movements = await _gather_material_movements(session, first, last)
    result.materials_sent = len(movements)
    try:
        result.materials_response = await onec_client.send_materials(period, movements)
    except Exception as exc:
        logger.error("send_materials failed: %s", exc)
        result.errors.append(f"materials: {exc}")

    # 3. Accounting transactions (derived from acts + movements)
    transactions = _build_transactions(period, acts, movements)
    result.transactions_sent = len(transactions)
    try:
        result.transactions_response = await onec_client.send_transactions(period, transactions)
    except Exception as exc:
        logger.error("send_transactions failed: %s", exc)
        result.errors.append(f"transactions: {exc}")

    # 4. Timesheet
    timesheet_rows = await _gather_timesheet(session, first, last)
    result.timesheet_rows_sent = len(timesheet_rows)
    try:
        result.timesheet_response = await onec_client.send_timesheet(period, timesheet_rows)
    except Exception as exc:
        logger.error("send_timesheet failed: %s", exc)
        result.errors.append(f"timesheet: {exc}")

    return result
