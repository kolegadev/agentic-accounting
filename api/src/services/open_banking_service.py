"""Open Banking Feed Service — multi-provider abstraction layer.

Supports TrueLayer (primary UK), Plaid (secondary), Salt Edge (EU),
Yodlee (fallback). MVP implements stub/test mode with realistic mock data.
"""

from __future__ import annotations

import hashlib
import random
import uuid
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bank_account import BankAccount, BankTransaction
from src.validators.open_banking import (
    ConnectAccountRequest,
    ConnectionResponse,
    ConnectionStatusResponse,
    ProviderResponse,
    SyncAllResponse,
    SyncResponse,
)

PROVIDERS: list[dict] = [
    {
        "name": "truelayer",
        "display_name": "TrueLayer",
        "region": "UK",
        "description": "UK & European Open Banking aggregator. Primary provider for GBP accounts.",
    },
    {
        "name": "plaid",
        "display_name": "Plaid",
        "region": "UK",
        "description": "Global financial data platform. Secondary UK provider, primary US.",
    },
    {
        "name": "saltedge",
        "display_name": "Salt Edge",
        "region": "EU",
        "description": "PSD2-compliant Open Banking for European accounts.",
    },
    {
        "name": "yodlee",
        "display_name": "Envestnet | Yodlee",
        "region": "Global",
        "description": "Legacy financial data aggregator. Fallback for non-Open Banking banks.",
    },
    {
        "name": "test",
        "display_name": "Test Provider",
        "region": "UK",
        "description": "Mock provider for testing and development. Generates realistic UK bank transactions.",
    },
]

# In-memory store for connections (MVP: no DB table yet)
# Maps bank_account_id → connection metadata
_connections: dict[uuid.UUID, dict] = {}


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class OpenBankingError(Exception):
    """Base exception for Open Banking service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ProviderNotFoundError(OpenBankingError):
    """Provider not found."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Provider '{provider}' not found. Available: {', '.join(p['name'] for p in PROVIDERS)}",
            status_code=404,
        )


class AccountNotConnectedError(OpenBankingError):
    """Bank account not connected to any Open Banking provider."""

    def __init__(self, bank_account_id: uuid.UUID) -> None:
        super().__init__(
            f"Bank account '{bank_account_id}' is not connected to any Open Banking provider",
            status_code=404,
        )


class AlreadyConnectedError(OpenBankingError):
    """Bank account already connected."""

    def __init__(self, bank_account_id: uuid.UUID) -> None:
        super().__init__(
            f"Bank account '{bank_account_id}' is already connected",
            status_code=409,
        )


# ---------------------------------------------------------------------------
# MockOpenBankingProvider
# ---------------------------------------------------------------------------


class MockOpenBankingProvider:
    """Generates realistic UK bank transactions for testing.

    Simulates transaction data with plausible merchant names, amounts,
    references, and UK-specific transaction types.
    """

    UK_MERCHANTS: list[dict] = [
        {"name": "Tesco Stores Ltd", "category": "Groceries", "typical_amount": (1500, 8500)},
        {"name": "Sainsbury's Supermarkets", "category": "Groceries", "typical_amount": (1200, 6000)},
        {"name": "Amazon UK", "category": "Online Retail", "typical_amount": (500, 5000)},
        {"name": "Deliveroo", "category": "Food Delivery", "typical_amount": (800, 3500)},
        {"name": "Pret A Manger", "category": "Food & Drink", "typical_amount": (300, 1500)},
        {"name": "Costa Coffee", "category": "Food & Drink", "typical_amount": (200, 800)},
        {"name": "Transport for London", "category": "Travel", "typical_amount": (250, 3000)},
        {"name": "BP Petrol Station", "category": "Fuel", "typical_amount": (3000, 9000)},
        {"name": "Shell UK", "category": "Fuel", "typical_amount": (2500, 8000)},
        {"name": "BT Group", "category": "Utilities", "typical_amount": (2000, 6000)},
        {"name": "Vodafone UK", "category": "Telecoms", "typical_amount": (1500, 4500)},
        {"name": "British Gas", "category": "Utilities", "typical_amount": (4000, 12000)},
        {"name": "Thames Water", "category": "Utilities", "typical_amount": (1500, 5000)},
        {"name": "Direct Line Insurance", "category": "Insurance", "typical_amount": (3000, 12000)},
        {"name": "HMRC", "category": "Tax", "typical_amount": (10000, 50000)},
        {"name": "Companies House", "category": "Government", "typical_amount": (500, 1500)},
        {"name": "Wix.com", "category": "Software", "typical_amount": (800, 3000)},
        {"name": "Google Workspace", "category": "Software", "typical_amount": (400, 1500)},
        {"name": "Slack Technologies", "category": "Software", "typical_amount": (500, 1200)},
        {"name": "GitHub Inc", "category": "Software", "typical_amount": (300, 800)},
        {"name": "Dropbox", "category": "Software", "typical_amount": (600, 1200)},
        {"name": "Royal Mail", "category": "Postage", "typical_amount": (100, 600)},
        {"name": "DHL Express", "category": "Shipping", "typical_amount": (800, 3000)},
        {"name": "WeWork UK", "category": "Rent", "typical_amount": (30000, 80000)},
        {"name": "Regus", "category": "Rent", "typical_amount": (20000, 60000)},
    ]

    UK_CLIENTS: list[dict] = [
        {"name": "Acme Corp Ltd", "typical_amount": (10000, 50000)},
        {"name": "TechStart UK", "typical_amount": (15000, 80000)},
        {"name": "Global Marketing Ltd", "typical_amount": (5000, 30000)},
        {"name": "BrightDesign Studio", "typical_amount": (10000, 60000)},
        {"name": "London Consulting Group", "typical_amount": (40000, 120000)},
    ]

    REFERENCE_PREFIXES: list[str] = [
        "INV-", "RCT-", "PAY-", "SUB-", "FEE-", "BILL-", "REF-", "TRN-",
    ]

    UK_SORT_CODES: list[str] = [
        "20-00-00", "40-00-00", "60-00-00", "30-00-00", "77-00-00",
    ]

    UK_ACCOUNT_PREFIXES: list[str] = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

    @classmethod
    def _random_ref(cls) -> str:
        """Generate a random transaction reference."""
        prefix = random.choice(cls.REFERENCE_PREFIXES)
        return f"{prefix}{random.randint(1000, 999999)}"

    @classmethod
    def _random_sort_code(cls) -> str:
        """Generate a random UK sort code."""
        return random.choice(cls.UK_SORT_CODES)

    @classmethod
    def _random_account_number(cls) -> str:
        """Generate a random UK account number (8 digits)."""
        return "".join(random.choice(cls.UK_ACCOUNT_PREFIXES + cls.UK_ACCOUNT_PREFIXES) for _ in range(8))

    @classmethod
    def generate_transactions(
        cls,
        bank_account_id: uuid.UUID,
        from_date: date,
        to_date: date,
        count: int = 10,
        opening_balance: int = 0,
    ) -> list[dict]:
        """Generate realistic UK bank transactions.

        Args:
            bank_account_id: UUID of the bank account.
            from_date: Start date for transaction generation.
            to_date: End date for transaction generation.
            count: Number of transactions to generate (default 10).
            opening_balance: Starting balance in pence.

        Returns:
            List of transaction dicts with: date, description, amount,
            reference, type, bank_detail.
        """
        transactions: list[dict] = []
        date_range = (to_date - from_date).days
        if date_range < 0:
            date_range = 0

        for i in range(count):
            # Random date within range
            day_offset = random.randint(0, date_range)
            tx_date = from_date + timedelta(days=day_offset)

            # 70% debits (money out), 30% credits (money in)
            is_credit = random.random() < 0.30

            if is_credit:
                client = random.choice(cls.UK_CLIENTS)
                min_amt, max_amt = client["typical_amount"]
                amount = random.randint(min_amt, max_amt)
                description = client["name"]
                tx_type = "CREDIT"
                reference = f"{cls._random_ref()} {client['name']}"
            else:
                merchant = random.choice(cls.UK_MERCHANTS)
                min_amt, max_amt = merchant["typical_amount"]
                # Debits are negative; typical_amount stored as (small, large) abs values
                amount = -random.randint(min_amt, max_amt)
                description = merchant["name"]
                tx_type = random.choice(["DEBIT", "DD", "SO", "CP"])
                if tx_type == "DD":
                    reference = f"DIRECT DEBIT REF {random.randint(100000, 999999)}"
                elif tx_type == "SO":
                    reference = f"STANDING ORDER {cls._random_ref()}"
                elif tx_type == "CP":
                    reference = f"CARD PAYMENT {random.randint(1000, 9999)} {merchant['name'][:10]}"
                else:
                    reference = cls._random_ref()

            transactions.append({
                "date": tx_date,
                "description": description,
                "amount": amount,
                "reference": reference,
                "type": tx_type,
                "bank_detail": {
                    "sort_code": cls._random_sort_code(),
                    "account_number": cls._random_account_number(),
                },
            })

        # Sort by date
        transactions.sort(key=lambda t: t["date"])
        return transactions


# ---------------------------------------------------------------------------
# OpenBankingService
# ---------------------------------------------------------------------------


class OpenBankingService:
    """Multi-provider Open Banking feed service.

    Provides connect/disconnect/sync operations for bank accounts linked
    to Open Banking providers. MVP implements a test mode with realistic
    mock transaction generation.
    """

    PROVIDER_NAMES: list[str] = [p["name"] for p in PROVIDERS]

    # ------------------------------------------------------------------
    # Provider listing
    # ------------------------------------------------------------------

    @staticmethod
    def list_providers() -> list[ProviderResponse]:
        """List all available Open Banking providers."""
        results: list[ProviderResponse] = []
        for p in PROVIDERS:
            results.append(ProviderResponse(
                name=p["name"],
                display_name=p["display_name"],
                region=p.get("region", "UK"),
                description=p["description"],
                is_test=(p["name"] == "test"),
            ))
        return results

    # ------------------------------------------------------------------
    # Connect
    # ------------------------------------------------------------------

    @staticmethod
    async def connect_account(
        db: AsyncSession,
        bank_account_id: uuid.UUID,
        provider: str,
        credentials: dict,
    ) -> ConnectionResponse:
        """Connect a bank account to an Open Banking provider.

        In test mode: creates an in-memory connection record.
        In production: would initiate OAuth/consent flow with the provider.

        Args:
            db: Database session.
            bank_account_id: UUID of the bank account to connect.
            provider: Provider name (truelayer, plaid, saltedge, yodlee, test).
            credentials: Provider-specific credentials.

        Returns:
            ConnectionResponse with connection details.

        Raises:
            BankAccountNotFoundError: If bank account does not exist.
            ProviderNotFoundError: If provider is not recognised.
            AlreadyConnectedError: If account is already connected.
        """
        # Validate provider
        valid_providers = [p["name"] for p in PROVIDERS]
        if provider not in valid_providers:
            raise ProviderNotFoundError(provider)

        # Verify bank account exists
        from src.services.bank_service import BankAccountNotFoundError

        stmt = select(BankAccount).where(BankAccount.id == bank_account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise BankAccountNotFoundError(str(bank_account_id))

        # Check not already connected
        if bank_account_id in _connections:
            existing = _connections[bank_account_id]
            if existing["status"] == "connected":
                raise AlreadyConnectedError(bank_account_id)

        # Create connection
        connection_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        _connections[bank_account_id] = {
            "connection_id": connection_id,
            "bank_account_id": bank_account_id,
            "provider": provider,
            "status": "connected",
            "connected_at": now,
            "last_sync_at": None,
            "error_message": None,
        }

        return ConnectionResponse(
            connection_id=connection_id,
            bank_account_id=bank_account_id,
            provider=provider,
            status="connected",
            connected_at=now,
            last_sync_at=None,
            error_message=None,
        )

    # ------------------------------------------------------------------
    # Fetch transactions
    # ------------------------------------------------------------------

    @staticmethod
    async def fetch_transactions(
        db: AsyncSession,
        bank_account_id: uuid.UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> int:
        """Fetch new transactions from the connected provider.

        In test mode: generates realistic mock transactions via
        MockOpenBankingProvider and imports them as bank transactions.

        Args:
            db: Database session.
            bank_account_id: UUID of the connected bank account.
            from_date: Optional start date for transaction fetch.
            to_date: Optional end date for transaction fetch.

        Returns:
            Number of new transactions imported.

        Raises:
            AccountNotConnectedError: If account is not connected.
        """
        # Check connection
        if bank_account_id not in _connections:
            raise AccountNotConnectedError(bank_account_id)

        conn = _connections[bank_account_id]
        if conn["status"] != "connected":
            raise OpenBankingError(
                f"Account '{bank_account_id}' connection status is '{conn['status']}'",
                status_code=400,
            )

        # Default date range: last 30 days
        if to_date is None:
            to_date = date.today()
        if from_date is None:
            from_date = to_date - timedelta(days=30)

        # Get account for balance info
        stmt = select(BankAccount).where(BankAccount.id == bank_account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()

        # Generate mock transactions
        mock_provider = MockOpenBankingProvider()
        count = random.randint(8, 20)
        mock_txns = mock_provider.generate_transactions(
            bank_account_id=bank_account_id,
            from_date=from_date,
            to_date=to_date,
            count=count,
            opening_balance=account.opening_balance if account else 0,
        )

        # Collect existing hashes for duplicate detection
        existing_hashes_stmt = select(BankTransaction.import_hash).where(
            BankTransaction.bank_account_id == bank_account_id,
            BankTransaction.import_hash.isnot(None),
        )
        existing_result = await db.execute(existing_hashes_stmt)
        existing_hashes: set[str] = {
            h for h in existing_result.scalars().all() if h is not None
        }

        imported_count = 0
        for tx in mock_txns:
            # Compute import hash
            raw = f"{tx['date'].isoformat()}|{tx['amount']}|{tx['description']}"
            import_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

            if import_hash in existing_hashes:
                continue

            existing_hashes.add(import_hash)

            bank_tx = BankTransaction(
                bank_account_id=bank_account_id,
                date=tx["date"],
                description=tx["description"],
                amount=tx["amount"],
                reference=tx["reference"],
                type=tx["type"],
                import_hash=import_hash,
                status="imported",
            )
            db.add(bank_tx)
            imported_count += 1

        await db.commit()

        # Update last sync timestamp
        _connections[bank_account_id]["last_sync_at"] = datetime.now(timezone.utc)

        return imported_count

    # ------------------------------------------------------------------
    # Sync all
    # ------------------------------------------------------------------

    @staticmethod
    async def sync_all(db: AsyncSession) -> SyncAllResponse:
        """Sync all connected bank accounts.

        Returns:
            SyncAllResponse with per-account results.
        """
        results: dict[str, SyncResponse] = {}
        total_imported = 0
        total_skipped = 0
        accounts_synced = 0

        for account_id, conn in list(_connections.items()):
            if conn["status"] != "connected":
                continue

            try:
                imported = await OpenBankingService.fetch_transactions(db, account_id)
                results[str(account_id)] = SyncResponse(
                    account_id=account_id,
                    imported_count=imported,
                    skipped_count=0,
                    from_date=date.today() - timedelta(days=30),
                    to_date=date.today(),
                )
                total_imported += imported
                accounts_synced += 1
            except Exception:
                results[str(account_id)] = SyncResponse(
                    account_id=account_id,
                    imported_count=0,
                    skipped_count=0,
                )

        return SyncAllResponse(
            accounts_synced=accounts_synced,
            total_imported=total_imported,
            total_skipped=total_skipped,
            results=results,
        )

    # ------------------------------------------------------------------
    # Disconnect
    # ------------------------------------------------------------------

    @staticmethod
    async def disconnect_account(
        db: AsyncSession,
        bank_account_id: uuid.UUID,
    ) -> ConnectionResponse:
        """Disconnect a bank account from its Open Banking provider.

        Args:
            db: Database session.
            bank_account_id: UUID of the bank account to disconnect.

        Returns:
            ConnectionResponse with updated status.

        Raises:
            AccountNotConnectedError: If account is not connected.
        """
        if bank_account_id not in _connections:
            raise AccountNotConnectedError(bank_account_id)

        conn = _connections[bank_account_id]
        conn["status"] = "disconnected"
        now = datetime.now(timezone.utc)

        return ConnectionResponse(
            connection_id=conn["connection_id"],
            bank_account_id=conn["bank_account_id"],
            provider=conn["provider"],
            status="disconnected",
            connected_at=conn["connected_at"],
            last_sync_at=conn.get("last_sync_at"),
            error_message=None,
        )

    # ------------------------------------------------------------------
    # Get connection status
    # ------------------------------------------------------------------

    @staticmethod
    async def get_connection_status(
        db: AsyncSession,
        bank_account_id: uuid.UUID,
    ) -> ConnectionStatusResponse:
        """Get the connection status for a bank account.

        Args:
            db: Database session.
            bank_account_id: UUID of the bank account to query.

        Returns:
            ConnectionStatusResponse with current status.

        Raises:
            AccountNotConnectedError: If account is not connected.
        """
        if bank_account_id not in _connections:
            raise AccountNotConnectedError(bank_account_id)

        conn = _connections[bank_account_id]

        # Count transactions imported via this feed
        stmt = select(BankTransaction).where(
            BankTransaction.bank_account_id == bank_account_id,
        )
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        transaction_count = count_result.scalar_one()

        return ConnectionStatusResponse(
            bank_account_id=conn["bank_account_id"],
            provider=conn["provider"],
            status=conn.get("status", "unknown"),
            connected_at=conn["connected_at"],
            last_sync_at=conn.get("last_sync_at"),
            transaction_count=transaction_count,
            error_message=conn.get("error_message"),
        )
