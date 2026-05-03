"""Pydantic schemas for all /hs/boiler/* request/response bodies.

Field names use Russian (Cyrillic) keys to match 1C XDTO format.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Acts ─────────────────────────────────────────────────────────────────────

class MaterialLine(BaseModel):
    номенклатура: str
    количество: float
    цена: float


class ActItem(BaseModel):
    номер_акта: str
    дата: str
    котельная_id: int
    котельная_наименование: str
    бригада: str
    сумма: float
    материалы: list[MaterialLine] = Field(default_factory=list)


class ActsRequest(BaseModel):
    период: str
    акты: list[ActItem]


class ActsResponse(BaseModel):
    статус: str = "ok"
    получено_актов: int
    проведено_актов: int
    номера_документов_1с: list[str]
    сообщение: str


# ── Materials ─────────────────────────────────────────────────────────────────

class MaterialMovementItem(BaseModel):
    тип_операции: str
    дата: str
    номенклатура: str
    количество: float
    сумма: float
    наряд_номер: str
    котельная_наименование: str


class MaterialsRequest(BaseModel):
    период: str
    движения_материалов: list[MaterialMovementItem]


class MaterialsResponse(BaseModel):
    статус: str = "ok"
    получено: int
    проведено: int


# ── Transactions ──────────────────────────────────────────────────────────────

class TransactionItem(BaseModel):
    дата: str
    дебет_счёт: str
    кредит_счёт: str
    сумма: float
    содержание: str
    субконто_дт: Optional[str] = None
    субконто_кт: Optional[str] = None


class TransactionsRequest(BaseModel):
    период: str
    проводки: list[TransactionItem]


class TransactionsResponse(BaseModel):
    статус: str = "ok"
    проведено_проводок: int


# ── Timesheet ─────────────────────────────────────────────────────────────────

class TimesheetRow(BaseModel):
    сотрудник_id: int
    сотрудник_фио: str
    обычные_часы: float
    сверхурочные: float = 0.0
    отпуск: float = 0.0
    больничный: float = 0.0


class TimesheetRequest(BaseModel):
    период: str
    табель: list[TimesheetRow]


class TimesheetResponse(BaseModel):
    статус: str = "ok"
    получено_строк: int


# ── Payslips ──────────────────────────────────────────────────────────────────

class PayslipsRequest(BaseModel):
    период: str
    запрос: str = "сформировать_расчётные_листки"


class PayslipItem(BaseModel):
    сотрудник_id: int
    сотрудник_фио: str
    период: str
    к_выплате: float
    ссылка_pdf: str


class PayslipsResponse(BaseModel):
    статус: str = "ok"
    сформировано: int
    расчётные_листки: list[PayslipItem]


# ── Admin ─────────────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    актов: int
    движений_материалов: int
    проводок: int
    табель_строк: int
    расчётных_листков: int
