"""Unit tests for Contact routes using FastAPI TestClient with mocked service layer."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.index import app
from src.services.contact_service import ContactNotFoundError, DuplicateContactError
from src.validators.contact import ContactResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONTACT_ID = uuid.uuid4()
NOW = "2026-06-27T12:00:00Z"

SAMPLE_CONTACT_RESPONSE: dict = {
    "id": str(CONTACT_ID),
    "type": "customer",
    "name": "Acme Corp",
    "company": "Acme Ltd",
    "email": "info@acme.com",
    "phone": "+44 20 7946 0958",
    "address_line1": "10 Downing Street",
    "address_line2": None,
    "city": "London",
    "postcode": "SW1A 2AA",
    "country": "GB",
    "vat_number": "GB123456789",
    "payment_terms": "Net 30",
    "default_gl_account_id": None,
    "currency": "GBP",
    "status": "active",
    "total_invoiced": 0,
    "total_paid": 0,
    "total_owing": 0,
    "created_at": NOW,
    "updated_at": NOW,
}


def make_response(**overrides) -> ContactResponse:
    """Build a ContactResponse with defaults overridden."""
    data = SAMPLE_CONTACT_RESPONSE.copy()
    data.update(overrides)
    data["id"] = str(data.get("id", CONTACT_ID))
    return ContactResponse(**data)


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST / — create_contact
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_contact_success(client: TestClient) -> None:
    """Should create contact and return 201."""
    mock = make_response(code=None)  # ContactResponse doesn't have code...
    # Actually let me just use make_response normally

    with patch(
        "src.routes.contacts.ContactService.create_contact",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = make_response()
        response = client.post(
            "/api/v1/contacts/",
            json={"name": "Acme Corp", "type": "customer"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Corp"
    assert data["type"] == "customer"


@pytest.mark.asyncio
async def test_create_contact_duplicate(client: TestClient) -> None:
    """Should return 409 for duplicate contact."""
    with patch(
        "src.routes.contacts.ContactService.create_contact",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = DuplicateContactError("name", "Acme Corp")
        response = client.post(
            "/api/v1/contacts/",
            json={"name": "Acme Corp", "type": "customer"},
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_contact_validation_error(client: TestClient) -> None:
    """Should return 422 for invalid request body."""
    response = client.post(
        "/api/v1/contacts/",
        json={"name": "Test"},  # missing required 'type'
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_contact_invalid_type(client: TestClient) -> None:
    """Should return 422 for invalid contact type."""
    response = client.post(
        "/api/v1/contacts/",
        json={"name": "Test", "type": "invalid"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET / — list_contacts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_contacts_success(client: TestClient) -> None:
    """Should return list of contacts."""
    with patch(
        "src.routes.contacts.ContactService.list_contacts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([make_response()], 1)
        response = client.get("/api/v1/contacts/")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["contacts"]) == 1
    assert data["contacts"][0]["name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_list_contacts_with_filters(client: TestClient) -> None:
    """Should pass filter params to service."""
    with patch(
        "src.routes.contacts.ContactService.list_contacts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        response = client.get(
            "/api/v1/contacts/?type=customer&status=active&search=Acme&limit=10&offset=0"
        )

    assert response.status_code == 200
    mock_list.assert_called_once()
    kwargs = mock_list.call_args.kwargs
    assert kwargs["type"] == "customer"
    assert kwargs["status"] == "active"
    assert kwargs["search"] == "Acme"


@pytest.mark.asyncio
async def test_list_contacts_empty(client: TestClient) -> None:
    """Should return empty list."""
    with patch(
        "src.routes.contacts.ContactService.list_contacts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        response = client.get("/api/v1/contacts/")

    assert response.status_code == 200
    assert response.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /{contact_id} — get_contact
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_contact_success(client: TestClient) -> None:
    """Should return contact when found."""
    with patch(
        "src.routes.contacts.ContactService.get_contact",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = make_response()
        response = client.get(f"/api/v1/contacts/{CONTACT_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == str(CONTACT_ID)


@pytest.mark.asyncio
async def test_get_contact_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent contact."""
    with patch(
        "src.routes.contacts.ContactService.get_contact",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = None
        response = client.get(f"/api/v1/contacts/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /{contact_id} — update_contact
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_contact_success(client: TestClient) -> None:
    """Should update contact and return 200."""
    with patch(
        "src.routes.contacts.ContactService.update_contact",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.return_value = make_response(name="Updated Corp")
        response = client.patch(
            f"/api/v1/contacts/{CONTACT_ID}",
            json={"name": "Updated Corp"},
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Corp"


@pytest.mark.asyncio
async def test_update_contact_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent contact."""
    with patch(
        "src.routes.contacts.ContactService.update_contact",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.side_effect = ContactNotFoundError(str(uuid.uuid4()))
        response = client.patch(
            f"/api/v1/contacts/{uuid.uuid4()}",
            json={"name": "Nope"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_contact_duplicate(client: TestClient) -> None:
    """Should return 409 for duplicate on update."""
    with patch(
        "src.routes.contacts.ContactService.update_contact",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.side_effect = DuplicateContactError("email", "dup@example.com")
        response = client.patch(
            f"/api/v1/contacts/{CONTACT_ID}",
            json={"email": "dup@example.com"},
        )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# POST /{contact_id}/archive — archive_contact
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_archive_contact_success(client: TestClient) -> None:
    """Should archive contact and return 200."""
    with patch(
        "src.routes.contacts.ContactService.archive_contact",
        new_callable=AsyncMock,
    ) as mock_archive:
        mock_archive.return_value = make_response(status="archived")
        response = client.post(f"/api/v1/contacts/{CONTACT_ID}/archive")

    assert response.status_code == 200
    assert response.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_archive_contact_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent contact."""
    with patch(
        "src.routes.contacts.ContactService.archive_contact",
        new_callable=AsyncMock,
    ) as mock_archive:
        mock_archive.side_effect = ContactNotFoundError(str(uuid.uuid4()))
        response = client.post(f"/api/v1/contacts/{uuid.uuid4()}/archive")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /find-or-create — find_or_create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_or_create_existing(client: TestClient) -> None:
    """Should return 200 when contact found."""
    with patch(
        "src.routes.contacts.ContactService.find_or_create",
        new_callable=AsyncMock,
    ) as mock_foc:
        mock_foc.return_value = (make_response(), False)
        response = client.post(
            "/api/v1/contacts/find-or-create",
            params={"name": "Acme Corp", "email": "info@acme.com"},
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_find_or_create_new(client: TestClient) -> None:
    """Should return 201 when contact auto-created."""
    with patch(
        "src.routes.contacts.ContactService.find_or_create",
        new_callable=AsyncMock,
    ) as mock_foc:
        mock_foc.return_value = (make_response(name="New Supplier", type="supplier"), True)
        response = client.post(
            "/api/v1/contacts/find-or-create",
            params={"name": "New Supplier"},
        )

    assert response.status_code == 201
    assert response.json()["name"] == "New Supplier"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check(client: TestClient) -> None:
    """Should return ok for health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
