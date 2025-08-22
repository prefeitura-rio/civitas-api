"""
Unit tests para validação de placas e funções relacionadas.
"""
import pytest
import time
import asyncio
from tests.utils.plate_validator import validate_plate, normalize_plate, get_plate_format


class TestPlateValidation:
    """Testes para validação de placas"""

    def test_validate_plate_valid_mercosul_format(self, valid_plates_mercosul_format):
        """Testa placas no formato Mercosul válido (ABC1D23)"""
        for plate in valid_plates_mercosul_format:
            assert validate_plate(plate), f"Placa válida rejeitada: {plate}"
            assert get_plate_format(plate) == "mercosul"

    def test_validate_plate_valid_old_format(self, valid_plates_old_format):
        """Testa placas no formato antigo válido (ABC1234)"""
        for plate in valid_plates_old_format:
            assert validate_plate(plate), f"Placa válida rejeitada: {plate}"
            assert get_plate_format(plate) == "antigo"

    def test_validate_plate_invalid_format(self, invalid_plates):
        """Testa placas com formato inválido"""
        for plate in invalid_plates:
            if plate == "abc1234":  # Minúscula deve ser válida após normalização
                assert validate_plate(plate), f"Placa válida rejeitada: {plate}"
            else:
                assert not validate_plate(plate), f"Placa inválida aceita: {plate}"
                assert get_plate_format(plate) == "invalido"

    def test_validate_plate_case_insensitive(self):
        """Testa se a validação funciona com minúsculas"""
        test_cases = ["abc1234", "xyz1a23", "DeF2B67"]
        for plate in test_cases:
            assert validate_plate(plate)
            # Testa normalização
            normalized = normalize_plate(plate)
            assert normalized == plate.upper()

    def test_validate_plate_performance(self, valid_plates_old_format):
        """Testa performance da validação de placas"""
        plates = valid_plates_old_format * 250  # 1000 placas total
        
        start = time.perf_counter()
        results = [validate_plate(plate) for plate in plates]
        duration = time.perf_counter() - start
        
        assert all(results)
        assert duration < 0.1, f"Validação muito lenta: {duration:.4f}s"

    def test_plate_format_detection(self):
        """Testa detecção de formato de placa"""
        assert get_plate_format("ABC1234") == "antigo"
        assert get_plate_format("ABC1D23") == "mercosul"
        assert get_plate_format("INVALID") == "invalido"
        assert get_plate_format("") == "invalido"


class TestPlateDetails:
    """Testes mockados para busca de detalhes de placas"""

    @pytest.mark.asyncio
    async def test_mock_get_plate_details_success(self, mock_plate_details):
        """Testa mock de busca de placa bem-sucedida"""
        assert mock_plate_details["placa"] == "ABC1234"
        assert mock_plate_details["proprietario"] == "João Silva"
        assert "created_at" in mock_plate_details
        assert "updated_at" in mock_plate_details
        assert "modelo" in mock_plate_details
        assert "ano" in mock_plate_details

    @pytest.mark.asyncio  
    async def test_mock_plate_validation_before_lookup(self, invalid_plates, valid_plates_old_format, valid_plates_mercosul_format):
        """Testa que validação de placa deve ocorrer antes da busca"""
        for plate in invalid_plates:
            if plate != "abc1234":  # Minúscula é válida
                is_valid = validate_plate(plate)
                assert is_valid == False, f"Placa inválida passou na validação: {plate}"
            
        all_valid_plates = valid_plates_old_format + valid_plates_mercosul_format
        for plate in all_valid_plates:
            is_valid = validate_plate(plate)
            assert is_valid == True, f"Placa válida não passou na validação: {plate}"


@pytest.mark.asyncio
async def test_plate_validation_logic(valid_plates_old_format, invalid_plates):
    """Teste de validação com múltiplas placas usando o validador centralizado"""
    start = time.perf_counter()
    
    for plate in valid_plates_old_format:
        assert validate_plate(plate), f"Placa válida rejeitada: {plate}"
    
    for plate in invalid_plates:
        if plate != "abc1234":  # Minúscula é válida
            assert not validate_plate(plate), f"Placa inválida aceita: {plate}"
    
    duration = time.perf_counter() - start
    assert duration < 0.01, f"Validação muito lenta: {duration:.4f}s"


@pytest.mark.asyncio
async def test_batch_processing_performance():
    """Teste de processamento em lotes com concorrência"""
    
    async def mock_process_plate(plate: str):
        await asyncio.sleep(0.01)
        return {"plate": plate.upper(), "processed": True}
    
    plates = [f"ABC{i:04d}" for i in range(10)]
    
    start = time.perf_counter()
    sequential_results = []
    for plate in plates:
        result = await mock_process_plate(plate)
        sequential_results.append(result)
    sequential_time = time.perf_counter() - start
    
    start = time.perf_counter()
    batch_results = await asyncio.gather(*[mock_process_plate(plate) for plate in plates])
    batch_time = time.perf_counter() - start
    
    speedup = sequential_time / batch_time
    
    assert len(sequential_results) == 10
    assert len(batch_results) == 10
    assert speedup >= 3.0, f"Speedup insuficiente: {speedup:.2f}x"
    
    for result in batch_results:
        assert result["processed"] is True
        assert result["plate"].startswith("ABC")


@pytest.mark.asyncio
async def test_error_handling_performance():
    """Teste de performance no tratamento de erros"""
    invalid_inputs = ["", "ABC", "1234567", "TOOLONG123"]
    
    start = time.perf_counter()
    
    invalid_count = 0
    for invalid_input in invalid_inputs:
        if not validate_plate(invalid_input):
            invalid_count += 1
    
    duration = time.perf_counter() - start
    
    assert duration < 0.001, f"Error handling muito lento: {duration:.4f}s"
    assert invalid_count == len(invalid_inputs)


@pytest.mark.asyncio
async def test_edge_cases():
    """Testa casos extremos de validação"""
    edge_cases = [
        (None, False),
        (123, False),
        ("   ABC1234   ", True),  # Com espaços
        ("ABC-1234", False),      # Com hífen
        ("ABC.1234", False),      # Com ponto
        ("ÀBC1234", False),       # Com acento
        ("0BC1234", False),       # Primeiro char numérico
    ]
    
    for case, expected in edge_cases:
        try:
            result = validate_plate(case)
            assert result == expected, f"Caso {case}: esperado {expected}, obtido {result}"
        except Exception as e:
            if expected:
                pytest.fail(f"Caso {case} deveria ser válido mas gerou erro: {e}")