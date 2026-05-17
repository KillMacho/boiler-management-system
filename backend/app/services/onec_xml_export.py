"""Generate XML files for 1C import from DB data."""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func

from app.models.requests import Act, WorkOrder
from app.models.warehouse import MaterialMovement
from app.models.personnel import Employee, Timesheet

EXPORT_DIR = Path("reports/onec-export")


def _pretty_xml(root: ET.Element) -> str:
    raw = ET.tostring(root, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="    ", encoding=None)


def _parse_period(period: str) -> tuple[date, date]:
    year, month = int(period[:4]), int(period[5:7])
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return first, last


class OneCXMLExporter:

    def __init__(self, session: AsyncSession):
        self._session = session
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    async def export_acts_for_period(self, period: str) -> str:
        first, last = _parse_period(period)

        rows = await self._session.execute(
            select(Act)
            .join(Act.work_order)
            .options(
                selectinload(Act.work_order).selectinload(WorkOrder.brigade),
                selectinload(Act.work_order).selectinload(WorkOrder.request),
                selectinload(Act.work_order)
                .selectinload(WorkOrder.material_movements)
                .selectinload(MaterialMovement.material),
            )
            .where(
                func.cast(Act.generated_at, __import__("sqlalchemy").Date) >= first,
                func.cast(Act.generated_at, __import__("sqlalchemy").Date) <= last,
            )
        )
        acts = list(rows.scalars().all())

        root = ET.Element("Выгрузка", ТипДанных="Акты", Период=period)

        for act in acts:
            wo = act.work_order
            boiler = wo.request.boiler if wo and wo.request else None
            brigade = wo.brigade if wo else None

            doc = ET.SubElement(root, "Документ")
            ET.SubElement(doc, "Номер").text = act.number or ""
            ET.SubElement(doc, "Дата").text = act.generated_at.date().isoformat()
            ET.SubElement(doc, "Котельная").text = boiler.name if boiler else ""
            ET.SubElement(doc, "Заказчик").text = ""
            ET.SubElement(doc, "БригадаНаименование").text = brigade.name if brigade else ""

            materials_list = []
            total_mat = Decimal("0")
            if wo:
                for mv in wo.material_movements:
                    if mv.movement_type == "outcome" and mv.material:
                        qty = mv.quantity
                        price = mv.material.price or Decimal("0")
                        summa = qty * price
                        total_mat += summa
                        materials_list.append((mv.material.name, qty, price, summa))

            ET.SubElement(doc, "СуммаУслуг").text = str(act.total_amount - total_mat if act.total_amount > total_mat else 0)
            ET.SubElement(doc, "СуммаМатериалов").text = str(total_mat)
            ET.SubElement(doc, "ВсегоКОплате").text = str(act.total_amount)

            mats_el = ET.SubElement(doc, "Материалы")
            for name, qty, price, summa in materials_list:
                mat = ET.SubElement(mats_el, "Материал")
                ET.SubElement(mat, "Номенклатура").text = name
                ET.SubElement(mat, "Количество").text = str(qty)
                ET.SubElement(mat, "Цена").text = str(price)
                ET.SubElement(mat, "Сумма").text = str(summa)

        path = EXPORT_DIR / f"acts_{period}.xml"
        path.write_text(_pretty_xml(root), encoding="utf-8")
        return str(path)

    async def export_materials_for_period(self, period: str) -> str:
        first, last = _parse_period(period)

        rows = await self._session.execute(
            select(MaterialMovement)
            .options(
                selectinload(MaterialMovement.material),
                selectinload(MaterialMovement.work_order).selectinload(WorkOrder.request),
            )
            .where(
                MaterialMovement.movement_type == "outcome",
                func.cast(MaterialMovement.created_at, __import__("sqlalchemy").Date) >= first,
                func.cast(MaterialMovement.created_at, __import__("sqlalchemy").Date) <= last,
            )
        )
        movements = list(rows.scalars().all())

        root = ET.Element("Выгрузка", ТипДанных="Материалы", Период=period)

        for mv in movements:
            wo = mv.work_order
            boiler_name = (
                wo.request.boiler.name if wo and wo.request and wo.request.boiler else ""
            )
            mat = mv.material
            if not mat:
                continue
            price = mat.price or Decimal("0")
            summa = mv.quantity * price

            doc = ET.SubElement(root, "Документ")
            ET.SubElement(doc, "Дата").text = mv.created_at.date().isoformat()
            ET.SubElement(doc, "Котельная").text = boiler_name
            ET.SubElement(doc, "СуммаМатериалов").text = str(summa)

            mats_el = ET.SubElement(doc, "Материалы")
            mat_el = ET.SubElement(mats_el, "Материал")
            ET.SubElement(mat_el, "Номенклатура").text = mat.name
            ET.SubElement(mat_el, "Количество").text = str(mv.quantity)
            ET.SubElement(mat_el, "Цена").text = str(price)
            ET.SubElement(mat_el, "Сумма").text = str(summa)

        path = EXPORT_DIR / f"materials_{period}.xml"
        path.write_text(_pretty_xml(root), encoding="utf-8")
        return str(path)

    async def export_timesheet_for_period(self, period: str) -> str:
        first, last = _parse_period(period)

        rows = await self._session.execute(
            select(Timesheet)
            .options(selectinload(Timesheet.employee))
            .where(Timesheet.date >= first, Timesheet.date <= last)
        )
        timesheets = list(rows.scalars().all())

        root = ET.Element("Выгрузка", ТипДанных="Табель", Период=period)
        doc = ET.SubElement(root, "Документ")
        ET.SubElement(doc, "Дата").text = first.isoformat()
        ET.SubElement(doc, "Котельная").text = ""

        mats_el = ET.SubElement(doc, "Материалы")
        agg: dict[int, dict] = {}
        for ts in timesheets:
            emp = ts.employee
            if not emp:
                continue
            eid = ts.employee_id
            if eid not in agg:
                fio = f"{emp.last_name} {emp.first_name}"
                if emp.middle_name:
                    fio += f" {emp.middle_name}"
                agg[eid] = {"фио": fio, "часы": Decimal("0")}
            agg[eid]["часы"] += ts.hours_worked

        for info in agg.values():
            mat = ET.SubElement(mats_el, "Материал")
            ET.SubElement(mat, "Номенклатура").text = info["фио"]
            ET.SubElement(mat, "Количество").text = str(info["часы"])
            ET.SubElement(mat, "Цена").text = "0"
            ET.SubElement(mat, "Сумма").text = "0"

        path = EXPORT_DIR / f"timesheet_{period}.xml"
        path.write_text(_pretty_xml(root), encoding="utf-8")
        return str(path)
