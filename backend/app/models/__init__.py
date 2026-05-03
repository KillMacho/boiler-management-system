"""ORM models package.

Importing submodules registers all mappers on the Base metadata.
"""
from app.models.base import Base  # noqa: F401
from app.models.boilers import (  # noqa: F401
    Boiler,
    Equipment,
    EquipmentCategory,
    EquipmentPassport,
)
from app.models.customers import Customer  # noqa: F401
from app.models.maintenance import (  # noqa: F401
    MaintenancePlanItem,
    MaintenanceRegulation,
    MaintenanceSchedule,
    MaintenanceType,
)
from app.models.ml import MLPrediction  # noqa: F401
from app.models.personnel import (  # noqa: F401
    Brigade,
    BrigadeMember,
    Department,
    Employee,
    EmployeeContact,
    EmployeeQualification,
    Position,
    Qualification,
    Timesheet,
    WorkTypeQualification,
)
from app.models.requests import (  # noqa: F401
    Act,
    Request,
    RequestPriority,
    RequestType,
    WorkOrder,
    WorkOrderChecklistItem,
    WorkOrderPhoto,
)
from app.models.telemetry import Telemetry, Threshold  # noqa: F401
from app.models.users import AuditLog, Role, User, UserRole  # noqa: F401
from app.models.reporting import RegulatoryReport  # noqa: F401
from app.models.warehouse import (  # noqa: F401
    Material,
    MaterialCategory,
    MaterialMovement,
    MaterialStock,
    PurchaseRequest,
    Warehouse,
)

__all__ = [
    "Base",
    "Boiler",
    "Equipment",
    "EquipmentCategory",
    "EquipmentPassport",
    "Customer",
    "MaintenancePlanItem",
    "MaintenanceRegulation",
    "MaintenanceSchedule",
    "MaintenanceType",
    "MLPrediction",
    "Brigade",
    "BrigadeMember",
    "Department",
    "Employee",
    "EmployeeContact",
    "EmployeeQualification",
    "Position",
    "Qualification",
    "Timesheet",
    "WorkTypeQualification",
    "Act",
    "Request",
    "RequestPriority",
    "RequestType",
    "WorkOrder",
    "WorkOrderChecklistItem",
    "WorkOrderPhoto",
    "Telemetry",
    "Threshold",
    "AuditLog",
    "Role",
    "User",
    "UserRole",
    "Material",
    "MaterialCategory",
    "MaterialMovement",
    "MaterialStock",
    "PurchaseRequest",
    "Warehouse",
    "RegulatoryReport",
]
