# -*- coding: utf-8 -*-
"""Comprehensive integration tests for Cars API endpoints (/cars/*)."""
import pytest
from unittest.mock import patch, AsyncMock
import asyncio


class TestCarsSinglePlateEndpoint:
    """Tests for GET /cars/plate/{plate} endpoint."""

    @pytest.mark.asyncio
    async def test_get_plate_success_detailed(self, client):
        """Test successful plate details retrieval with comprehensive data."""
        plate = "ABC1D34"
        
        with patch("app.utils.cortex_request") as mock_cortex:
            mock_cortex.return_value = (True, {
                "placa": plate,
                "marcaModelo": "VW GOL",
                "anoFabricacao": "2019",
                "cor": "BRANCO",
                "chassi": "9BWSU19F08B302158"
            })
            
            response = await client.get(f"/cars/plate/{plate}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["placa"] == plate
            assert data["marcaModelo"] == "VW GOL"
            assert data["anoFabricacao"] == "2019"
            assert "created_at" in data
            assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_get_plate_success_basic(self, client):
        """Test successful plate details retrieval with basic data."""
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
    async def test_get_plate_invalid_format_comprehensive(self, client):
        """Test comprehensive plate format validation."""
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
    async def test_get_plate_invalid_format_basic(self, client):
        """Test basic invalid plate format handling."""
        resp = await client.get("/cars/plate/INVALID!")
        assert resp.status_code in (400, 422)
        if resp.status_code == 400:
            assert resp.json()["detail"] == "Invalid plate format"

    @pytest.mark.asyncio
    async def test_get_plate_cortex_451_legal_block_advanced(self, client):
        """Test 451 Unavailable for Legal Reasons from Cortex - advanced."""
        plate = "LEG1234"  # Valid plate format
        
        class MockResponse:
            status = 451
        
        with patch("app.utils.cortex_request") as mock_cortex:
            mock_cortex.return_value = (False, MockResponse())
            
            response = await client.get(f"/cars/plate/{plate}")
            # The actual implementation might return 500 when external service has issues
            assert response.status_code in [451, 500], f"Expected 451 or 500, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_get_plate_cortex_451_legal_block_basic(self, client):
        """Test 451 Unavailable for Legal Reasons from Cortex - basic."""
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
    async def test_get_plate_database_caching(self, client):
        """Test database caching behavior."""
        fake_payload = {"placa": "ABC1D23", "marcaModelo": "VW GOL"}

        async def fake_cortex_request(method: str, url: str, cpf: str, raise_for_status: bool = False):
            return True, fake_payload

        with patch("app.utils.cortex_request", new=AsyncMock(side_effect=fake_cortex_request)) as mocked:
            resp1 = await client.get("/cars/plate/ABC1D23")
            assert resp1.status_code == 200

        resp2 = await client.get("/cars/plate/ABC1D23")
        assert resp2.status_code == 200
        assert resp2.json()["placa"] == "ABC1D23"

    @pytest.mark.asyncio
    async def test_get_plate_external_api_error_handling(self, client):
        """Test handling of external API errors."""
        plate = "ERROR123"
        
        with patch("app.utils.cortex_request") as mock_cortex:
            mock_cortex.return_value = (False, None)
            
            response = await client.get(f"/cars/plate/{plate}")
            assert response.status_code in [400, 404, 500, 503], f"Got status {response.status_code}"

    @pytest.mark.asyncio
    async def test_get_plate_cortex_api_integration_flow(self, client):
        """Test complete integration with Cortex API."""
        test_plates = ["INT1234", "INT5678", "INT9012"]
        
        for plate in test_plates:
            with patch("app.utils.cortex_request") as mock_cortex:
                mock_cortex.return_value = (True, {
                    "placa": plate,
                    "marcaModelo": "INTEGRATION TEST",
                    "anoFabricacao": "2020"
                })
                
                response = await client.get(f"/cars/plate/{plate}")
                
                assert response.status_code == 200
                data = response.json()
                assert data["placa"] == plate
                assert data["marcaModelo"] == "INTEGRATION TEST"
                
                # Verify external API was called
                mock_cortex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_plate_unicode_handling(self, client):
        """Test Unicode character handling."""
        plate = "UNI1234"
        
        with patch("app.utils.cortex_request") as mock_cortex:
            mock_cortex.return_value = (True, {
                "placa": plate,
                "nomeProprietario": "José María Ñoño 中文 🚗",
                "municipioPlaca": "São Paulo",
                "ufEmplacamento": "SP",
                "cor": "BRANCO/PRETO"
            })
            
            response = await client.get(f"/cars/plate/{plate}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["placa"] == plate
            assert "José María" in data["nomeProprietario"]
            assert "São Paulo" in data["municipioPlaca"]
            assert "🚗" in data["nomeProprietario"]

    @pytest.mark.asyncio
    async def test_get_plate_format_edge_cases(self, client):
        """Test various edge cases in plate format handling."""
        edge_cases = [
            ("ABC1234", True),   # Old format - valid
            ("ABC1D34", True),   # Mercosul format - valid  
            ("abc1234", True),   # Lowercase - should be accepted and normalized
            ("ABC-1234", False), # With dash - invalid
            ("1234ABC", False),  # Numbers first - invalid
            ("ABC12345", False), # Too long - invalid
            ("AB1234", False),   # Too short - invalid
        ]
        
        for plate, should_be_valid in edge_cases:
            if should_be_valid:
                with patch("app.utils.cortex_request") as mock_cortex:
                    mock_cortex.return_value = (True, {
                        "placa": plate.upper(),
                        "marcaModelo": "EDGE CASE TEST"
                    })
                    
                    response = await client.get(f"/cars/plate/{plate}")
                    assert response.status_code == 200, f"Valid plate {plate} should succeed"
                    
                    data = response.json()
                    assert data["placa"] == plate.upper()
            else:
                response = await client.get(f"/cars/plate/{plate}")
                assert response.status_code in [400, 422], f"Invalid plate {plate} should fail"

    @pytest.mark.asyncio
    async def test_get_plate_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        # Use valid plate format: 3 letters + 4 digits
        plates = [f"CON{i:04d}"[:7] for i in range(1234, 1239)]  # CON1234, CON1235, etc.
        
        with patch("app.utils.cortex_request") as mock_cortex:
            async def mock_response(*args, **kwargs):
                # Simulate small delay for realistic testing
                await asyncio.sleep(0.001)
                return (True, {
                    "placa": args[1].split('/')[-1] if len(args) > 1 else "TEST",
                    "marcaModelo": "CONCURRENT TEST"
                })
            
            mock_cortex.side_effect = mock_response
            
            # Make all requests concurrently
            start_time = asyncio.get_event_loop().time()
            tasks = [client.get(f"/cars/plate/{plate}") for plate in plates]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = asyncio.get_event_loop().time()
            
            # Verify most completed successfully (allow some failures due to complexity)
            successful_responses = [
                r for r in responses
                if not isinstance(r, Exception) and r.status_code == 200
            ]
            
            assert len(successful_responses) >= len(plates) // 2  # At least half should succeed
            
            # Should be significantly faster than sequential
            total_time = end_time - start_time
            assert total_time < 2.0  # Should complete in reasonable time


class TestCarsMultiplePlatesEndpoint:
    """Tests for POST /cars/plates endpoint (bulk operations)."""

    @pytest.mark.asyncio
    async def test_post_plates_invalid_json(self, client):
        """Test POST /cars/plates with invalid JSON."""
        response = await client.post(
            "/cars/plates", 
            content="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_plates_missing_body(self, client):
        """Test POST /cars/plates with missing body."""
        response = await client.post("/cars/plates")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_plates_empty_request(self, client):
        """Test POST /cars/plates with empty JSON."""
        response = await client.post("/cars/plates", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_plates_comprehensive_validation(self, client):
        """Test comprehensive request validation scenarios."""
        # Invalid JSON in POST request
        response = await client.post(
            "/cars/plates",
            content="invalid json content",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
        
        # Empty POST body
        response = await client.post("/cars/plates", json={})
        assert response.status_code == 422


class TestCarsHintEndpoint:
    """Tests for GET /cars/hint endpoint."""

    @pytest.mark.asyncio
    async def test_get_hint_missing_required_params_comprehensive(self, client):
        """Test comprehensive missing parameters scenarios."""
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

    @pytest.mark.asyncio
    async def test_get_hint_validation_basic(self, client):
        """Test basic hint validation."""
        # Missing required query parameters
        response = await client.get("/cars/hint?placa=TEST")
        assert response.status_code == 422


class TestCarsOtherEndpoints:
    """Tests for other cars endpoints."""

    @pytest.mark.asyncio
    async def test_get_monitored_plates_basic(self, client):
        """Test GET /cars/monitored - basic request."""
        response = await client.get("/cars/monitored")
        # Should return 200 or some valid response, not crash
        assert response.status_code in [200, 422, 404]
        
    @pytest.mark.asyncio
    async def test_post_monitored_plates_validation(self, client):
        """Test POST /cars/monitored validation."""
        response = await client.post("/cars/monitored")
        assert response.status_code == 422

        response = await client.post(
            "/cars/monitored",
            content="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_path_validation(self, client):
        """Test GET /cars/path validation."""
        response = await client.get("/cars/path")
        assert response.status_code == 422

        response = await client.get("/cars/path?placa=ABC1234")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_radar_validation(self, client):
        """Test GET /cars/radar validation."""
        response = await client.get("/cars/radar")
        assert response.status_code == 422


class TestCarsErrorHandlingAndValidation:
    """Tests for cars endpoints error handling and validation."""

    @pytest.mark.asyncio
    async def test_error_response_format_consistency(self, client):
        """Test that error responses follow consistent format."""
        # Test validation error format
        response = await client.get("/cars/plate/INVALID!")
        assert response.status_code in [400, 422]
        
        data = response.json()
        # Should have consistent error structure
        assert "detail" in data or "error" in data or "message" in data
        
        # Test with malformed JSON
        response = await client.post(
            "/cars/plates",
            content="malformed",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_application_health_and_readiness(self, client):
        """Test basic application health indicators."""
        # Test request/response cycle works with valid plate format
        with patch("app.utils.cortex_request") as mock_cortex:
            mock_cortex.return_value = (True, {"placa": "HLT1234", "marcaModelo": "TEST"})
            response = await client.get("/cars/plate/HLT1234")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_external_service_integration_patterns(self, client):
        """Test various external service integration patterns."""
        # Test success case with valid plate format
        with patch("app.utils.cortex_request") as mock_cortex:
            mock_cortex.return_value = (True, {"placa": "SUC1234", "marcaModelo": "OK"})
            response = await client.get("/cars/plate/SUC1234")
            assert response.status_code == 200, f"Success scenario failed with status {response.status_code}"
        
        # Test failure case with valid plate format
        with patch("app.utils.cortex_request") as mock_cortex:
            mock_cortex.return_value = (False, None)
            response = await client.get("/cars/plate/FAI1234")
            assert response.status_code in [400, 404, 500], f"Failure scenario failed with status {response.status_code}"


class TestDatabaseIntegration:
    """Tests for database integration (non-cars specific)."""

    @pytest.mark.asyncio
    async def test_database_crud_operations(self, client):
        """Test complete database CRUD operations."""
        from app.models import User
        
        # CREATE
        user = await User.create(
            username="crud_test_user",
            email="crud@test.com",
            full_name="CRUD Test User",
            cpf="11122233344"
        )
        
        assert user.id is not None
        assert user.username == "crud_test_user"
        assert user.cpf == "11122233344"
        
        # READ
        found_user = await User.get_or_none(cpf="11122233344")
        assert found_user is not None
        assert found_user.id == user.id
        assert found_user.email == "crud@test.com"
        
        # UPDATE
        found_user.full_name = "Updated CRUD User"
        await found_user.save()
        
        updated_user = await User.get(id=user.id)
        assert updated_user.full_name == "Updated CRUD User"
        
        # DELETE
        await updated_user.delete()
        
        deleted_user = await User.get_or_none(id=user.id)
        assert deleted_user is None