import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_plate_details_happy_path(client):
    fake_payload = {
        "placa": "ABC1D23",
        "marcaModelo": "VW GOL",
        "anoFabricacao": "2019",
    }

    async def fake_cortex_request(method: str, url: str, cpf: str, raise_for_status: bool = False):
        assert method == "GET"
        assert "/emplacamentos/placa/ABC1D23" in url
        return True, fake_payload

    with patch("app.utils.cortex_request", new=AsyncMock(side_effect=fake_cortex_request)):
        resp = await client.get("/cars/plate/ABC1D23")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["placa"] == "ABC1D23"
    assert data["marcaModelo"] == "VW GOL"
    assert "created_at" in data and data["created_at"] is not None
    assert "updated_at" in data and data["updated_at"] is not None


@pytest.mark.asyncio
async def test_get_plate_details_invalid_plate_returns_400(client):
    resp = await client.get("/cars/plate/INVALID!")
    assert resp.status_code in (400, 422)
    if resp.status_code == 400:
        assert resp.json()["detail"] == "Invalid plate format"


@pytest.mark.asyncio
async def test_get_plate_details_cortex_451_translates_to_451(client):
    import aiohttp

    class _FakeClientResponse(aiohttp.ClientResponse):
        pass

    async def fake_cortex_request(method: str, url: str, cpf: str, raise_for_status: bool = False):
        resp = object.__new__(_FakeClientResponse)
        resp.status = 451
        return False, resp

    with patch("app.utils.cortex_request", new=AsyncMock(side_effect=fake_cortex_request)):
        resp = await client.get("/cars/plate/ABC1D23")

    assert resp.status_code == 451
    assert resp.json()["detail"] == "Unavailable for legal reasons. CPF might be blocked."


@pytest.mark.asyncio
async def test_get_plate_details_caches_on_db(client):
    fake_payload = {"placa": "ABC1D23", "marcaModelo": "VW GOL"}

    async def fake_cortex_request(method: str, url: str, cpf: str, raise_for_status: bool = False):
        return True, fake_payload

    with patch("app.utils.cortex_request", new=AsyncMock(side_effect=fake_cortex_request)) as mocked:
        resp1 = await client.get("/cars/plate/ABC1D23")
        assert resp1.status_code == 200

    resp2 = await client.get("/cars/plate/ABC1D23")
    assert resp2.status_code == 200
    assert resp2.json()["placa"] == "ABC1D23"
