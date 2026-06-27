"""Business logic for Bank Statement Import — BankService."""

from __future__ import annotations

import csv
import decimal
import hashlib
import io
import json
import uuid
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import ofxparse
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bank_account import BankAccount, BankTransaction
from src.validators.bank import (
    BankAccountCreate,
    BankAccountResponse,
    BankImportResult,
    BankTransactionResponse,
    CategorizeTransaction,
)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class BankServiceError(Exception):
    """Base exception for bank service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class BankAccountNotFoundError(BankServiceError):
    """Bank account not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Bank account '{identifier}' not found", status_code=404)


class BankTransactionNotFoundError(BankServiceError):
    """Bank transaction not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Bank transaction '{identifier}' not found", status_code=404)


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------


def _load_template(name: str) -> dict:
    """Load a named bank template from the templates directory."""
    templates_dir = Path(__file__).parent.parent / "bank_templates"
    path = templates_dir / f"{name.lower()}.json"
    if not path.exists():
        raise BankServiceError(f"Template '{name}' not found", status_code=404)
    with open(path, "r") as f:
        return json.load(f)


def _list_available_templates() -> list[str]:
    """List all available bank template names."""
    templates_dir = Path(__file__).parent.parent / "bank_templates"
    return sorted([p.stem for p in templates_dir.glob("*.json")])


# ---------------------------------------------------------------------------
# BankService
# ---------------------------------------------------------------------------


class BankService:
    """Stateless service for bank account CRUD and statement import."""

    # ------------------------------------------------------------------
    # Response mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _account_to_response(account: BankAccount) -> BankAccountResponse:
        """Map a BankAccount ORM instance to a response schema."""
        return BankAccountResponse.model_validate(account)

    @staticmethod
    def _transaction_to_response(
        tx: BankTransaction,
    ) -> BankTransactionResponse:
        """Map a BankTransaction ORM instance to a response schema."""
        # Build response dict with bank account name if relationship loaded
        data = {
            "id": tx.id,
            "bank_account_id": tx.bank_account_id,
            "bank_account_name": tx.bank_account.name if tx.bank_account else None,
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "reference": tx.reference,
            "type": tx.type,
            "fitid": tx.fitid,
            "import_hash": tx.import_hash,
            "status": tx.status,
            "matched_transaction_id": tx.matched_transaction_id,
            "contact_id": tx.contact_id,
            "category": tx.category,
            "created_at": tx.created_at,
        }
        return BankTransactionResponse(**data)

    # ------------------------------------------------------------------
    # Account CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def create_account(
        db: AsyncSession,
        data: BankAccountCreate,
    ) -> BankAccountResponse:
        """Create a new bank account."""
        account = BankAccount(
            name=data.name,
            sort_code=data.sort_code,
            account_number=data.account_number,
            iban=data.iban,
            currency=data.currency,
            opening_balance=data.opening_balance,
            current_balance=data.opening_balance,
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
        return BankService._account_to_response(account)

    @staticmethod
    async def get_account(
        db: AsyncSession,
        account_id: uuid.UUID,
    ) -> Optional[BankAccountResponse]:
        """Return a single bank account by ID, or None."""
        stmt = select(BankAccount).where(BankAccount.id == account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        return BankService._account_to_response(account) if account else None

    @staticmethod
    async def list_accounts(
        db: AsyncSession,
        include_inactive: bool = False,
    ) -> list[BankAccountResponse]:
        """List bank accounts, optionally including inactive ones."""
        stmt = select(BankAccount).order_by(BankAccount.name)
        if not include_inactive:
            stmt = stmt.where(BankAccount.is_active == True)  # noqa: E712
        result = await db.execute(stmt)
        accounts = list(result.scalars().all())
        return [BankService._account_to_response(a) for a in accounts]

    # ------------------------------------------------------------------
    # Hash computation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_import_hash(
        tx_date: date,
        amount: int,
        description: str,
    ) -> str:
        """Compute SHA-256 hex digest of (date, amount, description)."""
        raw = f"{tx_date.isoformat()}|{amount}|{description}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Column auto-detection
    # ------------------------------------------------------------------

    @staticmethod
    def _auto_detect_csv_columns(headers: list[str]) -> dict[str, str]:
        """Try to match CSV headers to known patterns.

        Returns a dict mapping purpose (date, description, amount, debit, credit,
        reference, type) to the actual column name found, or None if not found.
        """
        mapping: dict[str, Optional[str]] = {
            "date": None,
            "description": None,
            "amount": None,
            "debit": None,
            "credit": None,
            "reference": None,
            "type": None,
        }

        headers_lower = {h.strip().lower(): h.strip() for h in headers}

        # Date patterns
        date_patterns = ["date", "transaction date", "started date", "value date"]
        for pat in date_patterns:
            if pat in headers_lower:
                mapping["date"] = headers_lower[pat]
                break

        # Description patterns
        desc_patterns = [
            "description",
            "narrative",
            "transaction description",
            "counter party",
            "payee",
            "memo",
        ]
        for pat in desc_patterns:
            if pat in headers_lower:
                mapping["description"] = headers_lower[pat]
                break

        # Amount (single signed column)
        amount_patterns = ["amount", "value", "amount (gbp)", "amount (eur)"]
        for pat in amount_patterns:
            if pat in headers_lower:
                mapping["amount"] = headers_lower[pat]
                break

        # Debit
        debit_patterns = ["debit", "debit amount", "money out", "paid out", "withdrawn"]
        for pat in debit_patterns:
            if pat in headers_lower:
                mapping["debit"] = headers_lower[pat]
                break

        # Credit
        credit_patterns = ["credit", "credit amount", "money in", "paid in", "deposits"]
        for pat in credit_patterns:
            if pat in headers_lower:
                mapping["credit"] = headers_lower[pat]
                break

        # Reference patterns
        ref_patterns = ["reference", "transaction reference", "notes", "narration"]
        for pat in ref_patterns:
            if pat in headers_lower:
                mapping["reference"] = headers_lower[pat]
                break

        # Type patterns
        type_patterns = [
            "type",
            "transaction type",
            "money out / money in",
            "category",
        ]
        for pat in type_patterns:
            if pat in headers_lower:
                mapping["type"] = headers_lower[pat]
                break

        # Remove None entries
        return {k: v for k, v in mapping.items() if v is not None}

    # ------------------------------------------------------------------
    # CSV Import
    # ------------------------------------------------------------------

    @staticmethod
    async def import_csv(
        db: AsyncSession,
        account_id: uuid.UUID,
        file_content: bytes,
        template_name: Optional[str] = None,
    ) -> BankImportResult:
        """Parse CSV file and create BankTransactions.

        Uses either a named template or auto-detection for column mapping.
        Detects duplicates via SHA-256 import_hash.
        """
        errors: list[str] = []
        imported: list[BankTransaction] = []
        skipped_count: int = 0

        # Verify account exists
        stmt = select(BankAccount).where(BankAccount.id == account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise BankAccountNotFoundError(str(account_id))

        # Load column mapping from template or auto-detect
        column_mapping: dict[str, Optional[str]] = {}
        date_format: str = "%d/%m/%Y"

        if template_name:
            template = _load_template(template_name)
            column_mapping = template.get("column_mappings", {})
            date_format = template.get("date_format", "%d/%m/%Y")
        else:
            # Try all templates, use the first with non-empty auto-detect result
            pass  # We'll auto-detect from headers below

        # Decode and parse CSV
        text = file_content.decode("utf-8-sig")
        # Detect delimiter
        sample_line = text.split("\n")[0] if "\n" in text else text
        delimiter = ","
        if ";" in sample_line:
            delimiter = ";"
        elif "\t" in sample_line:
            delimiter = "\t"

        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        headers = reader.fieldnames or []

        # Auto-detect if no template used
        auto_mapping = BankService._auto_detect_csv_columns(headers)

        if not template_name:
            # Merge auto-detected into column_mapping
            column_mapping = {
                k: v
                for k, v in {
                    "date": None,
                    "description": None,
                    "amount": None,
                    "debit": None,
                    "credit": None,
                    "reference": None,
                    "type": None,
                }.items()
            }
            for k, v in auto_mapping.items():
                column_mapping[k] = v

        # Override with auto-detection even for templated imports as fallback
        if not column_mapping.get("date"):
            column_mapping["date"] = auto_mapping.get("date")

        # Check minimum required columns
        date_col = column_mapping.get("date")
        desc_col = column_mapping.get("description")

        if not date_col or not desc_col:
            raise BankServiceError(
                "Could not identify date and description columns. "
                "Please specify a template or ensure headers include date/description.",
                status_code=422,
            )

        amount_col = column_mapping.get("amount")
        debit_col = column_mapping.get("debit")
        credit_col = column_mapping.get("credit")

        if not amount_col and not (debit_col and credit_col):
            raise BankServiceError(
                "Could not identify amount column(s). "
                "Need either a single 'amount' or separate 'debit'/'credit' columns.",
                status_code=422,
            )

        ref_col = column_mapping.get("reference")
        type_col = column_mapping.get("type")

        # Collect existing hashes for duplicate detection
        existing_hashes_stmt = select(BankTransaction.import_hash).where(
            BankTransaction.bank_account_id == account_id,
            BankTransaction.import_hash.isnot(None),
        )
        existing_result = await db.execute(existing_hashes_stmt)
        existing_hashes: set[str] = {
            h for h in existing_result.scalars().all() if h is not None
        }

        # Parse rows
        for row_num, row in enumerate(reader, start=2):  # 1-indexed, header=1
            try:
                # Parse date
                date_str = row.get(date_col, "").strip()
                if not date_str:
                    errors.append(f"Row {row_num}: missing date")
                    skipped_count += 1
                    continue

                # Try multiple date formats
                parsed_date: Optional[date] = None
                for fmt in [date_format, "%d/%m/%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        parsed = datetime.strptime(date_str.strip(), fmt)
                        parsed_date = parsed.date()
                        break
                    except ValueError:
                        continue

                if parsed_date is None:
                    errors.append(f"Row {row_num}: invalid date '{date_str}'")
                    skipped_count += 1
                    continue

                # Parse description
                description = row.get(desc_col, "").strip()
                if not description:
                    errors.append(f"Row {row_num}: missing description")
                    skipped_count += 1
                    continue

                # Parse amount
                try:
                    if amount_col:
                        amount_str = row.get(amount_col, "0").strip()
                        # Remove currency symbols and commas
                        amount_str = amount_str.replace("£", "").replace("€", "").replace("$", "").replace(",", "")
                        if not amount_str or amount_str == "-":
                            amount_str = "0"
                        amount = int(Decimal(amount_str) * 100)
                    elif debit_col and credit_col:
                        debit_str = row.get(debit_col, "0").strip()
                        credit_str = row.get(credit_col, "0").strip()
                        debit_str = debit_str.replace("£", "").replace("€", "").replace("$", "").replace(",", "")
                        credit_str = credit_str.replace("£", "").replace("€", "").replace("$", "").replace(",", "")
                        if not debit_str or debit_str == "-":
                            debit_str = "0"
                        if not credit_str or credit_str == "-":
                            credit_str = "0"
                        debit_val = int(Decimal(debit_str) * 100)
                        credit_val = int(Decimal(credit_str) * 100)
                        # Positive = credit, negative = debit
                        if credit_val > 0:
                            amount = credit_val
                        elif debit_val > 0:
                            amount = -debit_val
                        else:
                            amount = 0
                    else:
                        errors.append(f"Row {row_num}: no amount column found")
                        skipped_count += 1
                        continue
                except (ValueError, decimal.InvalidOperation) as e:
                    errors.append(f"Row {row_num}: invalid amount - {e}")
                    skipped_count += 1
                    continue

                # Duplicate detection via hash
                import_hash = BankService._compute_import_hash(parsed_date, amount, description)
                if import_hash in existing_hashes:
                    skipped_count += 1
                    continue

                existing_hashes.add(import_hash)

                # Parse optional fields
                reference = row.get(ref_col, "").strip() if ref_col else None
                if reference == "":
                    reference = None

                tx_type = row.get(type_col, "").strip() if type_col else None
                if tx_type == "":
                    tx_type = None

                tx = BankTransaction(
                    bank_account_id=account_id,
                    date=parsed_date,
                    description=description,
                    amount=amount,
                    reference=reference,
                    type=tx_type,
                    import_hash=import_hash,
                    status="imported",
                )
                db.add(tx)
                imported.append(tx)

            except Exception as exc:
                errors.append(f"Row {row_num}: unexpected error - {exc}")
                skipped_count += 1
                continue

        await db.commit()

        return BankImportResult(
            imported_count=len(imported),
            skipped_count=skipped_count,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # OFX Import
    # ------------------------------------------------------------------

    @staticmethod
    async def import_ofx(
        db: AsyncSession,
        account_id: uuid.UUID,
        file_content: bytes,
    ) -> BankImportResult:
        """Parse OFX file and create BankTransactions.

        Supports OFX versions 1.02, 2.1, 2.2. Uses FITID for duplicate detection.
        """
        errors: list[str] = []
        imported: list[BankTransaction] = []
        skipped_count: int = 0

        # Verify account exists
        stmt = select(BankAccount).where(BankAccount.id == account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise BankAccountNotFoundError(str(account_id))

        # Parse OFX
        try:
            text = file_content.decode("utf-8-sig", errors="replace")
            parser = ofxparse.OfxParser()
            ofx = parser.parse(io.StringIO(text))
        except Exception as exc:
            raise BankServiceError(
                f"Failed to parse OFX file: {exc}",
                status_code=422,
            )

        # Collect existing FITIDs for duplicate detection
        existing_fitids_stmt = select(BankTransaction.fitid).where(
            BankTransaction.bank_account_id == account_id,
            BankTransaction.fitid.isnot(None),
        )
        existing_result = await db.execute(existing_fitids_stmt)
        existing_fitids: set[str] = {
            f for f in existing_result.scalars().all() if f is not None
        }

        # Get account-level transactions from OFX
        try:
            account_statement = ofx.account
            if account_statement is None:
                raise BankServiceError("OFX file contains no account statement", status_code=422)

            statement = account_statement.statement
            if statement is None:
                raise BankServiceError("OFX file contains no statement data", status_code=422)

            transactions = statement.transactions
        except Exception as exc:
            raise BankServiceError(
                f"Failed to extract transactions from OFX: {exc}",
                status_code=422,
            )

        if not transactions:
            return BankImportResult(
                imported_count=0,
                skipped_count=0,
                errors=["No transactions found in OFX file"],
            )

        for tx in transactions:
            try:
                # Duplicate detection via FITID
                fitid = getattr(tx, "id", None)
                if fitid is None:
                    errors.append("Transaction has no FITID, skipping")
                    skipped_count += 1
                    continue

                if fitid in existing_fitids:
                    skipped_count += 1
                    continue

                existing_fitids.add(fitid)

                # Extract fields
                tx_date: Optional[date] = None
                dt = getattr(tx, "date", None)
                if isinstance(dt, datetime):
                    tx_date = dt.date()
                elif isinstance(dt, date):
                    tx_date = dt
                elif dt is not None:
                    try:
                        tx_date = datetime.strptime(str(dt), "%Y%m%d").date()
                    except ValueError:
                        pass

                if tx_date is None:
                    errors.append(f"Could not parse date for FITID {fitid}, skipping")
                    skipped_count += 1
                    continue

                # OFX amount: positive = credit? Let's check. OFX amount is signed.
                # For bank transactions, positive = credit, negative = debit.
                amount_raw = getattr(tx, "amount", 0)
                if amount_raw is None:
                    amount_raw = 0

                try:
                    amount_pence = int(Decimal(str(amount_raw)) * 100)
                except (ValueError, decimal.InvalidOperation):
                    errors.append(f"Invalid amount for FITID {fitid}")
                    skipped_count += 1
                    continue

                description = getattr(tx, "memo", "") or getattr(tx, "payee", "") or getattr(tx, "name", "") or "Unknown"
                reference = getattr(tx, "checknum", None)
                tx_type = getattr(tx, "type", None)

                bank_tx = BankTransaction(
                    bank_account_id=account_id,
                    date=tx_date,
                    description=str(description)[:10000],
                    amount=amount_pence,
                    reference=str(reference) if reference else None,
                    type=str(tx_type) if tx_type else None,
                    fitid=str(fitid),
                    status="imported",
                )
                db.add(bank_tx)
                imported.append(bank_tx)

            except Exception as exc:
                errors.append(f"Error processing OFX transaction: {exc}")
                skipped_count += 1
                continue

        await db.commit()

        return BankImportResult(
            imported_count=len(imported),
            skipped_count=skipped_count,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Transaction listing
    # ------------------------------------------------------------------

    @staticmethod
    async def list_transactions(
        db: AsyncSession,
        account_id: uuid.UUID,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BankTransactionResponse], int]:
        """List bank transactions with optional filters."""
        stmt = select(BankTransaction).where(
            BankTransaction.bank_account_id == account_id
        )

        if status:
            stmt = stmt.where(BankTransaction.status == status)
        if date_from:
            stmt = stmt.where(BankTransaction.date >= date_from)
        if date_to:
            stmt = stmt.where(BankTransaction.date <= date_to)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch
        stmt = stmt.order_by(BankTransaction.date.desc(), BankTransaction.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        result = await db.execute(stmt)
        transactions = list(result.scalars().all())

        return [BankService._transaction_to_response(t) for t in transactions], total

    # ------------------------------------------------------------------
    # Categorize
    # ------------------------------------------------------------------

    @staticmethod
    async def categorize_transaction(
        db: AsyncSession,
        transaction_id: uuid.UUID,
        contact_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
    ) -> BankTransactionResponse:
        """Update category and/or contact on a bank transaction.

        Auto-transitions status to 'categorized' if currently 'imported'.
        """
        stmt = select(BankTransaction).where(BankTransaction.id == transaction_id)
        result = await db.execute(stmt)
        tx = result.scalar_one_or_none()

        if tx is None:
            raise BankTransactionNotFoundError(str(transaction_id))

        if contact_id is not None:
            tx.contact_id = contact_id
        if category is not None:
            tx.category = category

        # Auto-transition from imported → categorized
        if tx.status == "imported" and (tx.category or tx.contact_id):
            tx.status = "categorized"

        await db.commit()
        await db.refresh(tx)
        return BankService._transaction_to_response(tx)
