"""Generate payslip PDF (Form T-51 simplified) using reportlab."""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger("payslip_pdf")

# Try to register a Cyrillic-capable font; fall back to Helvetica if unavailable.
_FONT_NAME = "Helvetica"
_FONT_NAME_BOLD = "Helvetica-Bold"

_FONTS_DIR = Path(__file__).parent.parent / "static" / "fonts"
for _candidate in ("DejaVuSans.ttf", "FreeSans.ttf", "Arial.ttf"):
    _path = _FONTS_DIR / _candidate
    if _path.exists():
        try:
            pdfmetrics.registerFont(TTFont("CyrillicFont", str(_path)))
            pdfmetrics.registerFont(
                TTFont(
                    "CyrillicFont-Bold",
                    str(_FONTS_DIR / _candidate.replace(".ttf", "Bold.ttf"))
                    if (_FONTS_DIR / _candidate.replace(".ttf", "Bold.ttf")).exists()
                    else str(_path),
                )
            )
            _FONT_NAME = "CyrillicFont"
            _FONT_NAME_BOLD = "CyrillicFont-Bold"
            logger.info("Cyrillic font registered: %s", _candidate)
        except Exception as exc:
            logger.warning("Could not register font %s: %s", _candidate, exc)
        break


@dataclass
class AccrualItem:
    name: str
    amount: float


@dataclass
class DeductionItem:
    name: str
    amount: float


@dataclass
class PayslipData:
    employee_id: int
    employee_name: str
    position: str
    department: str
    period: str  # e.g. "Апрель 2026"
    period_code: str  # e.g. "2026-04"
    accruals: list[AccrualItem] = field(default_factory=list)
    deductions: list[DeductionItem] = field(default_factory=list)
    days_worked: int = 0
    hours_worked: float = 0.0

    @property
    def total_accrued(self) -> float:
        return sum(a.amount for a in self.accruals)

    @property
    def total_deducted(self) -> float:
        return sum(d.amount for d in self.deductions)

    @property
    def net_pay(self) -> float:
        return self.total_accrued - self.total_deducted


def _fmt(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ")


def generate_payslip_pdf(data: PayslipData) -> bytes:
    """Return PDF bytes for one employee payslip."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "Normal", fontName=_FONT_NAME, fontSize=9, leading=12
    )
    bold = ParagraphStyle(
        "Bold", fontName=_FONT_NAME_BOLD, fontSize=10, leading=13
    )
    title_style = ParagraphStyle(
        "Title", fontName=_FONT_NAME_BOLD, fontSize=12, leading=15, alignment=1
    )

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("РАСЧЁТНЫЙ ЛИСТОК", title_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f"Организация: ООО «Котельный сервис» &nbsp;&nbsp; Период: {data.period}",
            normal,
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(f"Сотрудник: <b>{data.employee_name}</b>", normal))
    story.append(
        Paragraph(
            f"Должность: {data.position} &nbsp;&nbsp; Подразделение: {data.department}",
            normal,
        )
    )
    story.append(
        Paragraph(
            f"Отработано: {data.days_worked} дн. / {data.hours_worked:.1f} ч.",
            normal,
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    # ── Accruals table ────────────────────────────────────────────────────────
    story.append(Paragraph("Начислено:", bold))
    story.append(Spacer(1, 0.1 * cm))

    acc_rows = [["Вид начисления", "Сумма, руб."]]
    for item in data.accruals:
        acc_rows.append([item.name, _fmt(item.amount)])
    acc_rows.append(["ИТОГО начислено:", _fmt(data.total_accrued)])

    acc_table = Table(acc_rows, colWidths=[12 * cm, 5 * cm])
    acc_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), _FONT_NAME_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), _FONT_NAME),
                ("FONTNAME", (0, -1), (-1, -1), _FONT_NAME_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightyellow),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(acc_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── Deductions table ──────────────────────────────────────────────────────
    story.append(Paragraph("Удержано:", bold))
    story.append(Spacer(1, 0.1 * cm))

    ded_rows = [["Вид удержания", "Сумма, руб."]]
    for item in data.deductions:
        ded_rows.append([item.name, _fmt(item.amount)])
    ded_rows.append(["ИТОГО удержано:", _fmt(data.total_deducted)])

    ded_table = Table(ded_rows, colWidths=[12 * cm, 5 * cm])
    ded_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), _FONT_NAME_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), _FONT_NAME),
                ("FONTNAME", (0, -1), (-1, -1), _FONT_NAME_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.lightyellow),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(ded_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Net pay ───────────────────────────────────────────────────────────────
    net_table = Table(
        [["К ВЫПЛАТЕ:", _fmt(data.net_pay) + " руб."]],
        colWidths=[12 * cm, 5 * cm],
    )
    net_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#d4edda")),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 1, colors.green),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(net_table)
    story.append(Spacer(1, 0.5 * cm))
    story.append(
        Paragraph(
            "Документ сформирован автоматически системой управления котельной.",
            ParagraphStyle("Footer", fontName=_FONT_NAME, fontSize=7, textColor=colors.grey),
        )
    )

    doc.build(story)
    return buf.getvalue()


def save_payslip_pdf(data: PayslipData, output_dir: str | Path = "reports/payslips") -> Path:
    """Generate and save payslip PDF; return the file path."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    filename = f"payslip_{data.employee_id}_{data.period_code}.pdf"
    path = out / filename
    path.write_bytes(generate_payslip_pdf(data))
    logger.info("Payslip saved: %s", path)
    return path
