"""Role groups for RBAC. Single source of truth — used in routers via RoleChecker."""
from __future__ import annotations

from typing import List

ALL_ROLES: List[str] = [
    "dispatcher",
    "chief_engineer",
    "master",
    "brigade_leader",
    "operator",
    "storekeeper",
    "accountant",
    "hr_officer",
    "employee",
]

ALL_ADMIN: List[str] = ["chief_engineer", "dispatcher"]

WORK_ORDER_WRITE: List[str] = ALL_ADMIN + ["master", "brigade_leader"]
REQUEST_CREATE: List[str] = ALL_ADMIN + ["operator", "master", "brigade_leader"]
REQUEST_WRITE: List[str] = ALL_ADMIN + ["master", "brigade_leader"]
WAREHOUSE_WRITE: List[str] = ALL_ADMIN + ["storekeeper"]
HR_WRITE: List[str] = ALL_ADMIN + ["hr_officer"]
FINANCE_WRITE: List[str] = ALL_ADMIN + ["accountant"]
THRESHOLD_WRITE: List[str] = ALL_ADMIN
AUDIT_READ: List[str] = ALL_ADMIN
MAINTENANCE_WRITE: List[str] = ALL_ADMIN + ["master"]
BOILER_WRITE: List[str] = ALL_ADMIN
CUSTOMER_WRITE: List[str] = ALL_ADMIN + ["accountant"]

# Чтение разрешено всем 9 ролям.
READ_ANY: List[str] = list(ALL_ROLES)
