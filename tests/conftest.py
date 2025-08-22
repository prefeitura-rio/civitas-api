"""
Configurações e fixtures compartilhadas para os testes.
"""
import pytest


@pytest.fixture
def valid_plates_old_format():
    """Fixture com placas válidas no formato antigo."""
    return ["ABC1234", "XYZ5678", "DEF9012", "GHI3456"]


@pytest.fixture  
def valid_plates_mercosul_format():
    """Fixture com placas válidas no formato Mercosul."""
    return ["ABC1D23", "XYZ9A45", "DEF2B67", "GHI8C90"]


@pytest.fixture
def invalid_plates():
    """Fixture com placas inválidas."""
    return [
        "",           # Vazia
        "ABC",        # Muito curta
        "ABC12345",   # Muito longa
        "1234567",    # Só números
        "ABCDEFG",    # Só letras
        "AB1C234",    # Formato incorreto
        "ABC12D3",    # Posição errada da letra
        None,         # None
        "ABC 1234",   # Com espaço
        "abc1234",    # Minúscula (será normalizada)
    ]


@pytest.fixture
def mock_plate_details():
    """Fixture com dados mockados de detalhes de placa."""
    return {
        "placa": "ABC1234",
        "proprietario": "João Silva", 
        "modelo": "Honda Civic",
        "ano": "2020",
        "cor": "Branco",
        "cidade": "Rio de Janeiro",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_gps_points():
    """Fixture com pontos GPS mockados para testes de path."""
    return [
        {
            "lat": -22.9068 + (i * 0.0001), 
            "lng": -43.1729 + (i * 0.0001),
            "time": f"2025-01-01T{10 + (i % 12):02d}:{i % 60:02d}:00",
            "location": f"Location_{i}"
        }
        for i in range(100)
    ]