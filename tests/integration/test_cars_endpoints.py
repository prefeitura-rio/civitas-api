# -*- coding: utf-8 -*-
"""Integration tests for Cars API endpoints (/cars/*)."""
import pytest
from unittest.mock import AsyncMock, patch


class TestCarsPlateEndpoints:
    """Tests for /cars/plate/* endpoints."""

    @pytest.mark.asyncio
    async def test_get_single_plate_success(self, client):
        """Test GET /cars/plate/{plate} - successful plate details retrieval."""
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
    async def test_get_single_plate_invalid_format(self, client):
        """Test GET /cars/plate/{plate} - invalid plate format returns 400."""
        resp = await client.get("/cars/plate/INVALID!")
        assert resp.status_code in (400, 422)
        if resp.status_code == 400:
            assert resp.json()["detail"] == "Invalid plate format"

    @pytest.mark.asyncio
    async def test_get_single_plate_cortex_451_legal_block(self, client):
        """Test GET /cars/plate/{plate} - Cortex 451 legal block."""
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
    async def test_get_single_plate_database_caching(self, client):
        """Test GET /cars/plate/{plate} - database caching behavior."""
        fake_payload = {"placa": "ABC1D23", "marcaModelo": "VW GOL"}

        async def fake_cortex_request(method: str, url: str, cpf: str, raise_for_status: bool = False):
            return True, fake_payload

        with patch("app.utils.cortex_request", new=AsyncMock(side_effect=fake_cortex_request)) as mocked:
            resp1 = await client.get("/cars/plate/ABC1D23")
            assert resp1.status_code == 200

        resp2 = await client.get("/cars/plate/ABC1D23")
        assert resp2.status_code == 200
        assert resp2.json()["placa"] == "ABC1D23"


class TestCarsMultiplePlatesEndpoint:
    """Tests for /cars/plates endpoint (bulk operations)."""

    @pytest.mark.asyncio
    async def test_post_multiple_plates_invalid_json(self, client):
        """Test POST /cars/plates - invalid JSON format."""
        response = await client.post(
            "/cars/plates", 
            content="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_multiple_plates_missing_body(self, client):
        """Test POST /cars/plates - missing request body."""
        response = await client.post("/cars/plates")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_multiple_plates_empty_request(self, client):
        """Test POST /cars/plates - empty JSON object."""
        response = await client.post("/cars/plates", json={})
        assert response.status_code == 422


class TestCarsHintEndpoint:
    """Tests for /cars/hint endpoint."""

    @pytest.mark.asyncio
    async def test_get_hint_missing_required_params(self, client):
        """Test GET /cars/hint - missing required parameters."""
        # Missing all parameters
        response = await client.get("/cars/hint")
        assert response.status_code == 422

        # Missing start_time and end_time
        response = await client.get("/cars/hint?placa=TEST")
        assert response.status_code == 422
        
        # Missing placa
        response = await client.get(
            "/cars/hint?"
            "start_time=2024-01-01T00:00:00&"
            "end_time=2024-01-01T23:59:59"
        )
        assert response.status_code == 422


class TestCarsMonitoredPlatesEndpoint:
    """Tests for /cars/monitored endpoint."""

    @pytest.mark.asyncio
    async def test_get_monitored_plates_basic_request(self, client):
        """Test GET /cars/monitored - basic request works."""
        response = await client.get("/cars/monitored")
        # Should return 200 or some valid response, not crash
        assert response.status_code in [200, 422, 404]
        
    @pytest.mark.asyncio
    async def test_post_monitored_plates_missing_body(self, client):
        """Test POST /cars/monitored - missing request body."""
        response = await client.post("/cars/monitored")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_monitored_plates_invalid_json(self, client):
        """Test POST /cars/monitored - invalid JSON."""
        response = await client.post(
            "/cars/monitored",
            content="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422


class TestCarsPathEndpoint:
    """Tests for /cars/path endpoint."""

    @pytest.mark.asyncio
    async def test_get_path_missing_params(self, client):
        """Test GET /cars/path - missing required parameters."""
        response = await client.get("/cars/path")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_path_partial_params(self, client):
        """Test GET /cars/path - partial parameters."""
        response = await client.get("/cars/path?placa=ABC1234")
        assert response.status_code == 422


class TestCarsRadarEndpoint:
    """Tests for /cars/radar endpoint."""

    @pytest.mark.asyncio
    async def test_get_radar_missing_params(self, client):
        """Test GET /cars/radar - missing required parameters."""
        response = await client.get("/cars/radar")
        assert response.status_code == 422


class TestCarsValidationAndErrorHandling:
    """Tests for cars endpoints validation and error handling."""

    @pytest.mark.asyncio
    async def test_plate_format_validation_comprehensive(self, client):
        """Test comprehensive plate format validation across endpoints."""
        invalid_plates = [
            ("INVALID!", [400, 422]),    # Special characters
            ("ABC12345", [400, 422]),    # Too long
            ("AB123", [400, 422]),       # Too short
            ("", [404]),                 # Empty - returns 404 (not found)
        ]
        
        for invalid_plate, expected_codes in invalid_plates:
            response = await client.get(f"/cars/plate/{invalid_plate}")
            assert response.status_code in expected_codes, f"Failed for plate: {invalid_plate}, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_error_response_format_consistency(self, client):
        """Test that error responses follow consistent format across cars endpoints."""
        # Test validation error format
        response = await client.get("/cars/plate/INVALID!")
        assert response.status_code in [400, 422]
        
        data = response.json()
        # Should have consistent error structure
        assert "detail" in data or "error" in data or "message" in data
        
        # Test with malformed JSON on POST endpoint
        response = await client.post(
            "/cars/plates",
            content="malformed",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data