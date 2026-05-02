"""Warehouse business logic: reserve, write-off, receive, min-stock check."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import Material, MaterialMovement, MaterialStock, PurchaseRequest
from app.services import audit_service

logger = logging.getLogger("warehouse_service")


@dataclass
class MaterialLineItem:
    material_id: int
    quantity: Decimal


@dataclass
class ReserveResult:
    reserved: list[MaterialLineItem] = field(default_factory=list)
    purchase_requests_created: list[int] = field(default_factory=list)
    all_reserved: bool = True  # False if any purchase request was created


async def _find_best_stock(
    session: AsyncSession, material_id: int
) -> Optional[MaterialStock]:
    """Find the stock record with the most available (quantity - reserved_quantity)."""
    rows = await session.execute(
        select(MaterialStock).where(MaterialStock.material_id == material_id)
    )
    stocks = list(rows.scalars().all())
    if not stocks:
        return None
    best = max(stocks, key=lambda s: s.quantity - s.reserved_quantity)
    if best.quantity - best.reserved_quantity <= 0:
        return None
    return best


async def reserve_materials(
    session: AsyncSession,
    *,
    work_order_id: int,
    materials: list[MaterialLineItem],
    user_id: Optional[int] = None,
) -> ReserveResult:
    """Reserve materials for a work order.

    For each item:
    - If enough available stock exists → increase reserved_quantity, log 'reserve' movement.
    - If not enough → create a purchase_request for the deficit.

    Returns a ReserveResult describing what was reserved and what purchase requests were created.
    """
    result = ReserveResult()

    for item in materials:
        stock = await _find_best_stock(session, item.material_id)
        available = (stock.quantity - stock.reserved_quantity) if stock else Decimal("0")

        if stock and available >= item.quantity:
            # Full reservation possible
            stock.reserved_quantity += item.quantity
            movement = MaterialMovement(
                material_id=item.material_id,
                warehouse_id=stock.warehouse_id,
                movement_type="reserve",
                quantity=item.quantity,
                work_order_id=work_order_id,
            )
            session.add(movement)
            result.reserved.append(item)
            logger.info(
                "reserved material_id=%s qty=%s for work_order_id=%s",
                item.material_id,
                item.quantity,
                work_order_id,
            )
        else:
            # Insufficient stock — partial reserve what's available, create PR for remainder
            deficit = item.quantity
            if stock and available > 0:
                # Reserve what we can
                stock.reserved_quantity += available
                movement = MaterialMovement(
                    material_id=item.material_id,
                    warehouse_id=stock.warehouse_id,
                    movement_type="reserve",
                    quantity=available,
                    work_order_id=work_order_id,
                )
                session.add(movement)
                deficit = item.quantity - available
                result.reserved.append(MaterialLineItem(item.material_id, available))

            pr = PurchaseRequest(
                material_id=item.material_id,
                quantity=deficit,
                status="submitted",
            )
            session.add(pr)
            await session.flush()
            result.purchase_requests_created.append(pr.id)
            result.all_reserved = False
            logger.info(
                "created purchase_request id=%s for material_id=%s qty=%s",
                pr.id,
                item.material_id,
                deficit,
            )

    await session.commit()

    if result.purchase_requests_created:
        # Update work order status if work order is waiting for materials
        from app.models.requests import WorkOrder  # avoid circular

        wo = await session.get(WorkOrder, work_order_id)
        if wo and wo.status == "assigned":
            wo.status = "waiting_materials"
            await session.commit()

    await audit_service.log(
        session,
        user_id=user_id,
        action="materials_reserved",
        entity_type="work_order",
        entity_id=work_order_id,
        details={
            "reserved_count": len(result.reserved),
            "purchase_requests": result.purchase_requests_created,
        },
        autocommit=True,
    )
    return result


async def write_off_for_work_order(
    session: AsyncSession,
    *,
    work_order_id: int,
    user_id: Optional[int] = None,
) -> int:
    """Write off all previously reserved materials for a work order.

    Finds all 'reserve' movements for this work_order_id and converts them to
    'outcome' movements, decreasing both quantity and reserved_quantity.
    Returns the number of lines written off.
    """
    reserve_rows = await session.execute(
        select(MaterialMovement).where(
            MaterialMovement.work_order_id == work_order_id,
            MaterialMovement.movement_type == "reserve",
        )
    )
    reserve_movements = list(reserve_rows.scalars().all())
    count = 0

    for rm in reserve_movements:
        stock_row = await session.execute(
            select(MaterialStock).where(
                MaterialStock.material_id == rm.material_id,
                MaterialStock.warehouse_id == rm.warehouse_id,
            )
        )
        stock = stock_row.scalar_one_or_none()
        if stock:
            stock.quantity = max(Decimal("0"), stock.quantity - rm.quantity)
            stock.reserved_quantity = max(Decimal("0"), stock.reserved_quantity - rm.quantity)

        outcome = MaterialMovement(
            material_id=rm.material_id,
            warehouse_id=rm.warehouse_id,
            movement_type="outcome",
            quantity=rm.quantity,
            work_order_id=work_order_id,
        )
        session.add(outcome)
        count += 1

    if count > 0:
        await session.flush()
        await audit_service.log(
            session,
            user_id=user_id,
            action="write_off_materials",
            entity_type="work_order",
            entity_id=work_order_id,
            details={"lines_written_off": count},
        )

    return count


async def write_off_materials(
    session: AsyncSession,
    *,
    work_order_id: int,
    materials: list[MaterialLineItem],
    user_id: Optional[int] = None,
) -> list[MaterialMovement]:
    """Explicit write-off of a given list of materials (not from reservations)."""
    movements = []
    for item in materials:
        stock = await _find_best_stock(session, item.material_id)
        if not stock:
            logger.warning("no stock for material_id=%s, skipping write-off", item.material_id)
            continue
        stock.quantity = max(Decimal("0"), stock.quantity - item.quantity)
        stock.reserved_quantity = max(Decimal("0"), stock.reserved_quantity - item.quantity)
        movement = MaterialMovement(
            material_id=item.material_id,
            warehouse_id=stock.warehouse_id,
            movement_type="outcome",
            quantity=item.quantity,
            work_order_id=work_order_id,
        )
        session.add(movement)
        movements.append(movement)

    await session.flush()
    await audit_service.log(
        session,
        user_id=user_id,
        action="write_off_materials",
        entity_type="work_order",
        entity_id=work_order_id,
        details={"lines": len(movements)},
    )
    await session.commit()
    return movements


async def receive_materials(
    session: AsyncSession,
    *,
    material_id: int,
    warehouse_id: int,
    quantity: Decimal,
    purchase_request_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> MaterialMovement:
    """Receive materials into a warehouse (income movement).

    If purchase_request_id is provided, marks that purchase request as 'received'.
    Creates the MaterialStock record if it doesn't exist yet.
    """
    # Get or create stock record
    stock_row = await session.execute(
        select(MaterialStock).where(
            MaterialStock.material_id == material_id,
            MaterialStock.warehouse_id == warehouse_id,
        )
    )
    stock = stock_row.scalar_one_or_none()
    if stock is None:
        stock = MaterialStock(
            material_id=material_id,
            warehouse_id=warehouse_id,
            quantity=Decimal("0"),
            reserved_quantity=Decimal("0"),
        )
        session.add(stock)
        await session.flush()

    stock.quantity += quantity

    movement = MaterialMovement(
        material_id=material_id,
        warehouse_id=warehouse_id,
        movement_type="income",
        quantity=quantity,
        work_order_id=None,
    )
    session.add(movement)

    if purchase_request_id is not None:
        pr = await session.get(PurchaseRequest, purchase_request_id)
        if pr:
            pr.status = "received"

    await session.flush()
    await audit_service.log(
        session,
        user_id=user_id,
        action="materials_received",
        entity_type="material_stock",
        entity_id=stock.id,
        details={
            "material_id": material_id,
            "warehouse_id": warehouse_id,
            "quantity": str(quantity),
            "purchase_request_id": purchase_request_id,
        },
    )
    await session.commit()
    await session.refresh(movement)
    return movement


async def check_min_stock_levels(
    session: AsyncSession,
    *,
    user_id: Optional[int] = None,
) -> list[PurchaseRequest]:
    """Find materials below minimum stock and create purchase requests for each.

    Returns list of newly created PurchaseRequest records.
    """
    # Aggregate total quantity per material across all warehouses
    from sqlalchemy import func

    agg_rows = await session.execute(
        select(
            MaterialStock.material_id,
            func.sum(MaterialStock.quantity).label("total_qty"),
        ).group_by(MaterialStock.material_id)
    )
    totals: dict[int, Decimal] = {r[0]: r[1] for r in agg_rows.fetchall()}

    # Load all materials with min_stock > 0
    mat_rows = await session.execute(
        select(Material).where(Material.min_stock > 0)
    )
    materials = list(mat_rows.scalars().all())

    created: list[PurchaseRequest] = []
    for mat in materials:
        total = totals.get(mat.id, Decimal("0"))
        if total < mat.min_stock:
            # Check if pending purchase request already exists
            existing = (
                await session.execute(
                    select(PurchaseRequest).where(
                        PurchaseRequest.material_id == mat.id,
                        PurchaseRequest.status == "pending",
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                deficit = mat.min_stock - total
                pr = PurchaseRequest(
                    material_id=mat.id,
                    quantity=deficit,
                    status="submitted",
                )
                session.add(pr)
                await session.flush()
                created.append(pr)
                logger.info(
                    "min-stock alert: material_id=%s total=%s min=%s → PR id=%s qty=%s",
                    mat.id,
                    total,
                    mat.min_stock,
                    pr.id,
                    deficit,
                )

    if created:
        await audit_service.log(
            session,
            user_id=user_id,
            action="min_stock_check",
            entity_type="warehouse",
            details={"purchase_requests_created": [pr.id for pr in created]},
        )

    await session.commit()
    return created
