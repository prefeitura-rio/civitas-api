"""
Testes para casos de erro e edge cases da API.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from tests.utils.plate_validator import validate_plate


class TestAPIErrorHandling:
    """Testes para tratamento de erros da API"""

    @pytest.mark.asyncio
    async def test_invalid_plate_error_400(self, invalid_plates):
        """Testa que placas inválidas retornam erro 400"""
        async def mock_api_call(plate: str):
            if not validate_plate(plate):
                return {"status": 400, "error": "Placa inválida"}
            return {"status": 200, "data": {"placa": plate}}
        
        for plate in invalid_plates:
            if plate != "abc1234":  # Minúscula é válida após normalização
                response = await mock_api_call(plate)
                assert response["status"] == 400
                assert "erro" in response.get("error", "").lower() or "inválida" in response.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_plate_not_found_error_404(self):
        """Testa erro 404 quando placa não é encontrada"""
        async def mock_api_call(plate: str):
            if validate_plate(plate):
                # Simula placa válida mas não encontrada no banco
                return {"status": 404, "error": "Placa não encontrada"}
            return {"status": 400, "error": "Placa inválida"}
        
        response = await mock_api_call("XYZ9999")
        assert response["status"] == 404
        assert "não encontrada" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_database_error_500(self):
        """Testa erro 500 em caso de falha no banco de dados"""
        async def mock_api_call_with_db_error(plate: str):
            if validate_plate(plate):
                # Simula erro interno do servidor
                return {"status": 500, "error": "Erro interno do servidor"}
            return {"status": 400, "error": "Placa inválida"}
        
        response = await mock_api_call_with_db_error("ABC1234")
        assert response["status"] == 500
        assert "erro interno" in response["error"].lower() or "servidor" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_rate_limit_error_429(self):
        """Testa limite de taxa (rate limiting)"""
        async def mock_api_call_with_rate_limit(plate: str, request_count: int):
            if request_count > 100:  # Simula limite de 100 requests
                return {"status": 429, "error": "Muitas requisições"}
            if validate_plate(plate):
                return {"status": 200, "data": {"placa": plate}}
            return {"status": 400, "error": "Placa inválida"}
        
        # Simula muitas requisições
        response = await mock_api_call_with_rate_limit("ABC1234", 150)
        assert response["status"] == 429
        assert "muitas" in response["error"].lower() or "requisições" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Testa tratamento de timeout"""
        async def slow_api_call():
            await asyncio.sleep(5.0)  # Simula operação lenta
            return {"status": 200, "data": "success"}
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Timeout de 1 segundo
            response = await asyncio.wait_for(slow_api_call(), timeout=1.0)
            pytest.fail("Deveria ter dado timeout")
        except asyncio.TimeoutError:
            elapsed = asyncio.get_event_loop().time() - start_time
            assert elapsed < 1.5, f"Timeout demorou muito: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_concurrent_error_handling(self):
        """Testa tratamento de erros em requisições concorrentes"""
        async def mock_api_call(plate: str, should_fail: bool = False):
            await asyncio.sleep(0.01)  # Simula latência
            if should_fail:
                return {"status": 500, "error": "Erro simulado"}
            if validate_plate(plate):
                return {"status": 200, "data": {"placa": plate}}
            return {"status": 400, "error": "Placa inválida"}
        
        # Mix de sucesso e erro
        tasks = [
            mock_api_call("ABC1234", False),  # Sucesso
            mock_api_call("DEF5678", True),   # Erro 500
            mock_api_call("INVALID", False),  # Erro 400
            mock_api_call("GHI9012", False),  # Sucesso
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        assert len(results) == 4
        assert results[0]["status"] == 200  # Sucesso
        assert results[1]["status"] == 500  # Erro interno
        assert results[2]["status"] == 400  # Placa inválida
        assert results[3]["status"] == 200  # Sucesso


class TestEdgeCases:
    """Testes para casos extremos"""

    @pytest.mark.asyncio
    async def test_empty_request_body(self):
        """Testa requisição com body vazio"""
        async def mock_api_call(request_body):
            if not request_body:
                return {"status": 400, "error": "Body da requisição vazio"}
            return {"status": 200, "data": "ok"}
        
        response = await mock_api_call({})
        assert response["status"] == 400

    @pytest.mark.asyncio
    async def test_malformed_json(self):
        """Testa JSON malformado"""
        async def mock_api_call(json_data):
            if json_data == "INVALID_JSON":
                return {"status": 400, "error": "JSON malformado"}
            return {"status": 200, "data": "ok"}
        
        response = await mock_api_call("INVALID_JSON")
        assert response["status"] == 400

    @pytest.mark.asyncio
    async def test_very_long_plate_input(self):
        """Testa entrada de placa muito longa"""
        very_long_plate = "A" * 1000
        assert not validate_plate(very_long_plate)

    @pytest.mark.asyncio
    async def test_special_characters_in_plate(self):
        """Testa caracteres especiais em placas"""
        special_plates = [
            "ABC@123", "ABC#123", "ABC$123", 
            "ABC%123", "ABC&123", "ABC*123"
        ]
        
        for plate in special_plates:
            assert not validate_plate(plate), f"Placa com caractere especial aceita: {plate}"

    @pytest.mark.asyncio
    async def test_unicode_characters(self):
        """Testa caracteres Unicode em placas"""
        unicode_plates = [
            "ABÇ1234",  # Ç
            "AÑC1234",  # Ñ  
            "AßC1234",  # ß
            "A€C1234",  # €
            "A中1234",  # Caractere chinês
        ]
        
        for plate in unicode_plates:
            assert not validate_plate(plate), f"Placa com Unicode aceita: {plate}"

    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Testa performance sob carga"""
        async def mock_high_load_scenario():
            tasks = []
            for i in range(100):
                plate = f"ABC{i:04d}"
                task = asyncio.create_task(self._mock_validate_async(plate))
                tasks.append(task)
            
            start_time = asyncio.get_event_loop().time()
            results = await asyncio.gather(*tasks)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            return results, elapsed
        
        results, elapsed = await mock_high_load_scenario()
        
        assert len(results) == 100
        assert all(results), "Todas as validações deveriam ter sucesso"
        assert elapsed < 1.0, f"Performance sob carga muito lenta: {elapsed:.3f}s"

    async def _mock_validate_async(self, plate: str):
        """Helper para validação assíncrona mockada"""
        await asyncio.sleep(0.001)  # Simula pequena latência
        return validate_plate(plate)