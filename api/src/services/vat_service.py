"""Business logic for VAT Calculation & MTD Preview — VatService — Module 7."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.transaction import Posting, Transaction, VATLine
from src.models.vat import VatAdjustment, VatPeriod, VatReturn
from src.validators.vat import (
    VatAdjustmentCreate,
    VatAdjustmentResponse,
    VatAuditEntry,
    VatAuditResponse,
    VatPeriodCreate,
    VatPeriodListResponse,
    VatPeriodResponse,
    VatReturnCalculationResponse,
    VatReturnResponse,
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class VatServiceError(Exception):
    """Base exception for VAT service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class VatPeriodNotFoundError(VatServiceError):
    """VAT period not found."""

    def __init__(self, period_id: uuid.UUID) -> None:
        super().__init__(f"VAT period '{period_id}' not found", status_code=404)


class VatReturnNotFoundError(VatServiceError):
    """VAT return not found."""

    def __init__(self, return_id: uuid.UUID) -> None:
        super().__init__(f"VAT return '{return_id}' not found", status_code=404)


class VatPeriodClosedError(VatServiceError):
    """Attempted to calculate on a closed period."""

    def __init__(self, period_id: uuid.UUID) -> None:
        super().__init__(f"VAT period '{period_id}' is already closed", status_code=422)


class VatFlatRateMissingError(VatServiceError):
    """Flat rate scheme specified without percentage."""

    def __init__(self) -> None:
        super().__init__(
            "flat_rate_percentage is required when scheme is 'flat_rate'",
            status_code=422,
        )


class VatBoxOutOfRangeError(VatServiceError):
    """Adjustment box number out of range."""

    def __init__(self, box_number: int) -> None:
        super().__init__(
            f"Box number must be between 1 and 9, got {box_number}",
            status_code=422,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _period_to_response(period: VatPeriod) -> VatPeriodResponse:
    """Map an ORM VatPeriod to a VatPeriodResponse."""
    return VatPeriodResponse.model_validate(period)


def _return_to_response(vr: VatReturn) -> VatReturnResponse:
    """Map an ORM VatReturn to a VatReturnResponse."""
    return VatReturnResponse.model_validate(vr)


def _adjustment_to_response(adj: VatAdjustment) -> VatAdjustmentResponse:
    """Map an ORM VatAdjustment to a VatAdjustmentResponse."""
    return VatAdjustmentResponse.model_validate(adj)


# ---------------------------------------------------------------------------
# VatService
# ---------------------------------------------------------------------------


class VatService:
    """Stateless service for VAT periods, 9-box calculations, and audit trails.

    Supports three VAT schemes:
    - standard: VAT on invoice date (transaction effective_date)
    - cash: VAT on payment date (transaction recorded_at)
    - flat_rate: simplified % of gross turnover
    """

    # ------------------------------------------------------------------
    # Create period
    # ------------------------------------------------------------------

    @staticmethod
    async def create_period(
        db: AsyncSession,
        data: VatPeriodCreate,
    ) -> VatPeriodResponse:
        """Create a new VAT period.

        Raises:
            VatFlatRateMissingError if scheme is flat_rate but no percentage provided.
        """
        if data.scheme == "flat_rate" and data.flat_rate_percentage is None:
            raise VatFlatRateMissingError()

        period = VatPeriod(
            start_date=data.start_date,
            end_date=data.end_date,
            scheme=data.scheme,
            flat_rate_percentage=data.flat_rate_percentage,
        )
        db.add(period)
        await db.commit()
        await db.refresh(period)
        return _period_to_response(period)

    # ------------------------------------------------------------------
    # List periods
    # ------------------------------------------------------------------

    @staticmethod
    async def list_periods(
        db: AsyncSession,
        *,
        status: Optional[str] = None,
        scheme: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[VatPeriodResponse], int]:
        """List VAT periods with optional filters. Returns (items, total_count)."""
        stmt = select(VatPeriod)

        if status:
            stmt = stmt.where(VatPeriod.status == status)
        if scheme:
            stmt = stmt.where(VatPeriod.scheme == scheme)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch
        stmt = stmt.order_by(VatPeriod.start_date.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        periods = list(result.scalars().all())

        return [_period_to_response(p) for p in periods], total

    # ------------------------------------------------------------------
    # Get period
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_period(
        db: AsyncSession,
        period_id: uuid.UUID,
    ) -> VatPeriod:
        """Fetch a VatPeriod or raise VatPeriodNotFoundError."""
        period = await db.get(VatPeriod, period_id)
        if period is None:
            raise VatPeriodNotFoundError(period_id)
        return period

    # ------------------------------------------------------------------
    # Get return
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_return(
        db: AsyncSession,
        return_id: uuid.UUID,
    ) -> VatReturn:
        """Fetch a VatReturn with relationships or raise VatReturnNotFoundError."""
        vat_return = await db.get(
            VatReturn,
            return_id,
            options=[
                selectinload(VatReturn.adjustments),
                selectinload(VatReturn.period),
            ],
        )
        if vat_return is None:
            raise VatReturnNotFoundError(return_id)
        return vat_return

    # ------------------------------------------------------------------
    # Calculate 9-box return
    # ------------------------------------------------------------------

    @staticmethod
    async def calculate_return(
        db: AsyncSession,
        period_id: uuid.UUID,
    ) -> VatReturnCalculationResponse:
        """Calculate a 9-box VAT return for the given period.

        Queries transactions within the period date range and computes
        box figures based on VAT scheme.

        Raises:
            VatPeriodNotFoundError if period does not exist.
            VatPeriodClosedError if period is closed.
        """
        period = await VatService._get_period(db, period_id)

        if period.status == "closed":
            raise VatPeriodClosedError(period_id)

        # Determine which date column to use based on scheme
        if period.scheme == "cash":
            date_column = Transaction.recorded_at
        else:
            # standard and flat_rate use effective_date (invoice date)
            date_column = Transaction.effective_date

        # Fetch all posted transactions within the period range
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.postings)
                .selectinload(Posting.vat_lines),
                selectinload(Transaction.postings)
                .selectinload(Posting.account),
            )
            .where(
                Transaction.status == "posted",
                date_column >= period.start_date,
                date_column <= period.end_date,
            )
        )
        result = await db.execute(stmt)
        transactions = list(result.scalars().all())

        if period.scheme == "flat_rate":
            boxes, entries = VatService._calculate_flat_rate(
                transactions, period
            )
        else:
            # standard and cash both use VAT lines from postings
            boxes, entries = VatService._calculate_from_vat_lines(transactions)

        # Ensure box3 = box1 + box2, box5 = box3 - box4
        boxes["box3"] = boxes["box1"] + boxes["box2"]
        boxes["box5"] = boxes["box3"] - boxes["box4"]

        # Create VatReturn record
        vat_return = VatReturn(
            period_id=period_id,
            box1=boxes["box1"],
            box2=boxes["box2"],
            box3=boxes["box3"],
            box4=boxes["box4"],
            box5=boxes["box5"],
            box6=boxes["box6"],
            box7=boxes["box7"],
            box8=boxes["box8"],
            box9=boxes["box9"],
        )
        db.add(vat_return)
        await db.commit()
        await db.refresh(vat_return)

        # Build audit
        audit = VatAuditResponse(
            vat_return_id=vat_return.id,
            period=_period_to_response(period),
            entries=entries,
            summary=boxes,
        )

        return VatReturnCalculationResponse(
            vat_return=_return_to_response(vat_return),
            audit=audit,
        )

    # ------------------------------------------------------------------
    # Core calculation: from VAT lines (standard & cash)
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_from_vat_lines(
        transactions: list[Transaction],
    ) -> tuple[dict[str, int], list[VatAuditEntry]]:
        """Calculate 9-box figures from transactions' VAT lines.

        Returns (boxes_dict, audit_entries).
        """
        box1 = 0  # Output VAT
        box2 = 0  # EU acquisitions VAT (MVP: 0)
        box4 = 0  # Input VAT
        box6 = 0  # Total sales excl VAT
        box7 = 0  # Total purchases excl VAT
        box8 = 0  # EU sales (MVP: 0)
        box9 = 0  # EU acquisitions (MVP: 0)

        entries: list[VatAuditEntry] = []

        for txn in transactions:
            for posting in txn.postings:
                for vl in posting.vat_lines:
                    entry = VatAuditEntry(
                        source_type="vat_line",
                        source_id=vl.id,
                        source_reference=txn.reference,
                        description=txn.description,
                        vat_type=vl.vat_type,
                        vat_rate=vl.vat_rate,
                        amount=vl.vat_amount,
                        net_amount=vl.net_amount,
                        effective_date=txn.effective_date,
                    )

                    if vl.vat_type == "output":
                        box1 += vl.vat_amount
                        box6 += vl.net_amount
                        entry.box_number = 1
                    elif vl.vat_type == "input":
                        box4 += vl.vat_amount
                        box7 += vl.net_amount
                        entry.box_number = 4

                    entries.append(entry)

        boxes = {
            "box1": box1,
            "box2": box2,
            "box3": 0,  # computed after
            "box4": box4,
            "box5": 0,  # computed after
            "box6": box6,
            "box7": box7,
            "box8": box8,
            "box9": box9,
        }
        return boxes, entries

    # ------------------------------------------------------------------
    # Core calculation: flat rate
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_flat_rate(
        transactions: list[Transaction],
        period: VatPeriod,
    ) -> tuple[dict[str, int], list[VatAuditEntry]]:
        """Calculate 9-box figures using flat rate scheme.

        For flat rate:
        - box1 = flat_rate_percentage * gross_turnover
        - box4 = 0 (no input VAT reclaim in flat rate)
        - box6 = gross_turnover
        - box7 = total purchases excl VAT
        """
        if period.flat_rate_percentage is None:
            raise VatFlatRateMissingError()

        gross_turnover = 0  # Total sales including VAT
        box7 = 0  # Total purchases excl VAT
        entries: list[VatAuditEntry] = []

        for txn in transactions:
            for posting in txn.postings:
                for vl in posting.vat_lines:
                    if vl.vat_type == "output":
                        gross_turnover += vl.net_amount + vl.vat_amount
                    elif vl.vat_type == "input":
                        box7 += vl.net_amount

                    entries.append(
                        VatAuditEntry(
                            source_type="vat_line",
                            source_id=vl.id,
                            source_reference=txn.reference,
                            description=txn.description,
                            vat_type=vl.vat_type,
                            vat_rate=vl.vat_rate,
                            amount=vl.vat_amount,
                            net_amount=vl.net_amount,
                            effective_date=txn.effective_date,
                            box_number=1 if vl.vat_type == "output" else 7,
                        )
                    )

        # Flat rate: box1 = % of gross turnover
        rate = period.flat_rate_percentage / 100.0
        box1 = round(gross_turnover * rate)
        box4 = 0  # No input VAT reclaim in flat rate
        box6 = gross_turnover

        boxes = {
            "box1": box1,
            "box2": 0,
            "box3": 0,  # computed after
            "box4": box4,
            "box5": 0,  # computed after
            "box6": box6,
            "box7": box7,
            "box8": 0,
            "box9": 0,
        }
        return boxes, entries

    # ------------------------------------------------------------------
    # Get return
    # ------------------------------------------------------------------

    @staticmethod
    async def get_return(
        db: AsyncSession,
        return_id: uuid.UUID,
    ) -> Optional[VatReturnResponse]:
        """Return a single VAT return, or None if not found."""
        vat_return = await db.get(
            VatReturn,
            return_id,
            options=[selectinload(VatReturn.adjustments)],
        )
        if vat_return is None:
            return None
        return _return_to_response(vat_return)

    # ------------------------------------------------------------------
    # Add adjustment
    # ------------------------------------------------------------------

    @staticmethod
    async def add_adjustment(
        db: AsyncSession,
        return_id: uuid.UUID,
        data: VatAdjustmentCreate,
    ) -> VatAdjustmentResponse:
        """Add a manual adjustment to one box of a VAT return.

        Updates the box value and records the adjustment for audit trail.

        Raises:
            VatReturnNotFoundError if return does not exist.
            VatBoxOutOfRangeError if box_number is not 1-9.
        """
        vat_return = await VatService._get_return(db, return_id)

        if data.box_number < 1 or data.box_number > 9:
            raise VatBoxOutOfRangeError(data.box_number)

        # Get current box value
        box_attr = f"box{data.box_number}"
        amount_before = getattr(vat_return, box_attr)
        amount_after = amount_before + data.amount

        # Create adjustment record
        adjustment = VatAdjustment(
            vat_return_id=return_id,
            box_number=data.box_number,
            amount_before=amount_before,
            amount_after=amount_after,
            reason=data.reason,
            source_reference=data.source_reference,
        )
        db.add(adjustment)

        # Update the box value
        setattr(vat_return, box_attr, amount_after)

        # Recalculate dependent boxes
        vat_return.box3 = vat_return.box1 + vat_return.box2
        vat_return.box5 = vat_return.box3 - vat_return.box4

        await db.commit()
        await db.refresh(adjustment)

        return _adjustment_to_response(adjustment)

    # ------------------------------------------------------------------
    # Get audit trail
    # ------------------------------------------------------------------

    @staticmethod
    async def get_audit_trail(
        db: AsyncSession,
        return_id: uuid.UUID,
    ) -> VatAuditResponse:
        """Return the full audit trail for a VAT return.

        Includes period info, all source entries, and summary.

        Raises:
            VatReturnNotFoundError if return does not exist.
        """
        vat_return = await VatService._get_return(db, return_id)

        # Get period
        period = await VatService._get_period(db, vat_return.period_id)

        # Collect entries from adjustments
        entries: list[VatAuditEntry] = []
        for adj in vat_return.adjustments:
            entries.append(
                VatAuditEntry(
                    source_type="adjustment",
                    source_id=adj.id,
                    source_reference=adj.source_reference,
                    description=f"Manual adjustment: {adj.reason}",
                    box_number=adj.box_number,
                    amount=adj.amount_after - adj.amount_before,
                    effective_date=None,
                )
            )

        # Summary: current box values
        summary = {
            "box1": vat_return.box1,
            "box2": vat_return.box2,
            "box3": vat_return.box3,
            "box4": vat_return.box4,
            "box5": vat_return.box5,
            "box6": vat_return.box6,
            "box7": vat_return.box7,
            "box8": vat_return.box8,
            "box9": vat_return.box9,
        }

        return VatAuditResponse(
            vat_return_id=vat_return.id,
            period=_period_to_response(period),
            entries=entries,
            summary=summary,
        )
