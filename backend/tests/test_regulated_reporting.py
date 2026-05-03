"""Tests for regulated reporting XML generation (no DB required — uses stub employees)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services import regulated_reporting as rr


# All tests pass None as session to trigger stub employee fallback


@pytest.mark.asyncio
async def test_generate_6ndfl_creates_file():
    result = await rr.generate_6_ndfl(None, "2026-Q1")
    assert result.report_type == "6-NDFL"
    assert result.period == "2026-Q1"
    assert result.size_bytes > 0
    path = Path(result.filepath)
    assert path.exists()


@pytest.mark.asyncio
async def test_generate_6ndfl_valid_xml():
    result = await rr.generate_6_ndfl(None, "2026-Q1")
    from lxml import etree
    tree = etree.parse(result.filepath)
    root = tree.getroot()
    assert root.tag == "Файл"
    assert root.attrib.get("ВерсФорм") == "5.04"


@pytest.mark.asyncio
async def test_generate_6ndfl_contains_inn():
    result = await rr.generate_6_ndfl(None, "2026-Q1")
    content = Path(result.filepath).read_text(encoding="utf-8")
    assert rr.ORG_INN in content


@pytest.mark.asyncio
async def test_generate_6ndfl_contains_employees():
    result = await rr.generate_6_ndfl(None, "2026-Q1")
    content = Path(result.filepath).read_text(encoding="utf-8")
    assert "Иванов" in content


@pytest.mark.asyncio
async def test_generate_rsv_creates_valid_xml():
    result = await rr.generate_rsv(None, "2026-Q1")
    assert result.report_type == "RSV"
    from lxml import etree
    tree = etree.parse(result.filepath)
    root = tree.getroot()
    assert "Файл" in root.tag


@pytest.mark.asyncio
async def test_generate_4fss_creates_valid_xml():
    result = await rr.generate_4_fss(None, "2026-Q1")
    assert result.report_type == "4-FSS"
    from lxml import etree
    tree = etree.parse(result.filepath)
    root = tree.getroot()
    assert "Файл" in root.tag


@pytest.mark.asyncio
async def test_generate_szv_stazh_creates_valid_xml():
    result = await rr.generate_szv_stazh(None, 2026)
    assert result.report_type == "SZV-STAZH"
    from lxml import etree
    tree = etree.parse(result.filepath)
    root = tree.getroot()
    # Root tag contains СЗВ_СТАЖ
    assert "СТАЖ" in root.tag or "СЗВ" in root.tag


@pytest.mark.asyncio
async def test_generate_all_quarters():
    for q in range(1, 5):
        result = await rr.generate_6_ndfl(None, f"2026-Q{q}")
        assert Path(result.filepath).exists()


@pytest.mark.asyncio
async def test_generate_invalid_period_raises():
    with pytest.raises(ValueError, match="Invalid quarter period"):
        await rr.generate_6_ndfl(None, "2026-04")


@pytest.mark.asyncio
async def test_parse_quarter_correct():
    from datetime import date
    year, q, first, last = rr._parse_quarter("2026-Q1")
    assert year == 2026
    assert q == 1
    assert first == date(2026, 1, 1)
    assert last == date(2026, 3, 31)


@pytest.mark.asyncio
async def test_parse_quarter4():
    from datetime import date
    year, q, first, last = rr._parse_quarter("2025-Q4")
    assert q == 4
    assert first == date(2025, 10, 1)
    assert last == date(2025, 12, 31)


@pytest.mark.asyncio
async def test_stub_employees_have_ndfl():
    employees = rr._stub_employees()
    assert len(employees) > 0
    for emp in employees:
        assert float(emp["ndfl"]) > 0


@pytest.mark.asyncio
async def test_fmt_num():
    assert rr._fmt_num("1000") == "1000.00"
    assert rr._fmt_num(1234.5) == "1234.50"
