"""Tests for payslip PDF generator."""
from __future__ import annotations

import pytest

from app.services.payslip_pdf_generator import (
    AccrualItem,
    DeductionItem,
    PayslipData,
    generate_payslip_pdf,
)


def _make_data(**kwargs) -> PayslipData:
    defaults = dict(
        employee_id=1,
        employee_name="Иванов Иван Иванович",
        position="Оператор котельной",
        department="Котельный цех №1",
        period="Апрель 2026",
        period_code="2026-04",
        accruals=[AccrualItem("Оклад", 50000.0)],
        deductions=[DeductionItem("НДФЛ", 6500.0)],
        days_worked=22,
        hours_worked=176.0,
    )
    defaults.update(kwargs)
    return PayslipData(**defaults)


def test_generate_returns_bytes():
    data = _make_data()
    pdf = generate_payslip_pdf(data)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000  # non-trivial PDF


def test_pdf_starts_with_pdf_header():
    data = _make_data()
    pdf = generate_payslip_pdf(data)
    assert pdf[:4] == b"%PDF"


def test_net_pay_calculation():
    data = _make_data(
        accruals=[AccrualItem("Оклад", 50000.0), AccrualItem("Премия", 10000.0)],
        deductions=[DeductionItem("НДФЛ", 7800.0)],
    )
    assert data.total_accrued == 60000.0
    assert data.total_deducted == 7800.0
    assert abs(data.net_pay - 52200.0) < 0.01


def test_generate_with_no_deductions():
    data = _make_data(deductions=[])
    pdf = generate_payslip_pdf(data)
    assert isinstance(pdf, bytes)
    assert data.net_pay == data.total_accrued
