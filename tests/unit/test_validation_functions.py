import pytest
from app.utils import validate_cpf, validate_cnpj, validate_plate


class TestValidateCPF:
    """Casos de teste para função de validação de CPF."""
    
    def test_valid_cpfs(self):
        """Testa números de CPF válidos."""
        valid_cpfs = [
            "11144477735",  # Valid CPF
            "12345678909",  # Another valid CPF
            "00000000191",  # Valid CPF with leading zeros
        ]
        for cpf in valid_cpfs:
            assert validate_cpf(cpf) is True, f"CPF {cpf} should be valid"
    
    def test_valid_cpfs_with_formatting(self):
        """Testa números de CPF válidos com pontos e traços."""
        valid_cpfs = [
            "111.444.777-35",
            "123.456.789-09",
            "000.000.001-91",
        ]
        for cpf in valid_cpfs:
            assert validate_cpf(cpf) is True, f"CPF {cpf} should be valid"
    
    def test_invalid_cpfs_wrong_digits(self):
        """Testa números de CPF com dígitos verificadores errados."""
        invalid_cpfs = [
            "11144477736",  # Wrong last digit
            "12345678908",  # Wrong last digit
            "11144477725",  # Wrong second-to-last digit
        ]
        for cpf in invalid_cpfs:
            assert validate_cpf(cpf) is False, f"CPF {cpf} should be invalid"
    
    def test_invalid_cpfs_same_digits(self):
        """Testa números de CPF com todos os dígitos iguais (inválido)."""
        invalid_cpfs = [
            "11111111111",
            "22222222222",
            "33333333333",
            "00000000000",
        ]
        for cpf in invalid_cpfs:
            assert validate_cpf(cpf) is False, f"CPF {cpf} should be invalid"
    
    def test_invalid_cpfs_wrong_length(self):
        """Testa números de CPF com comprimento errado."""
        invalid_cpfs = [
            "1114447773",   # Too short
            "111444777355", # Too long
            "12345",        # Much too short
            "",             # Empty string
        ]
        for cpf in invalid_cpfs:
            assert validate_cpf(cpf) is False, f"CPF {cpf} should be invalid"
    
    def test_cpf_with_non_numeric_chars(self):
        """Testa CPF com caracteres não numéricos (devem ser ignorados)."""
        cpf_with_letters = "111abc444def777ghi35"
        assert validate_cpf(cpf_with_letters) is True, "Should extract only digits"


class TestValidateCNPJ:
    """Casos de teste para função de validação de CNPJ."""
    
    def test_valid_cnpjs(self):
        """Testa números de CNPJ válidos."""
        valid_cnpjs = [
            "11222333000181",  # Valid CNPJ
            "11444777000161",  # Another valid CNPJ
        ]
        for cnpj in valid_cnpjs:
            result = validate_cnpj(cnpj)
            assert result == cnpj, f"CNPJ {cnpj} should be valid and return the CNPJ"
    
    def test_valid_cnpjs_with_formatting(self):
        """Testa números de CNPJ válidos com pontos, barras e traços."""
        valid_cnpjs = [
            "11.222.333/0001-81",
            "11.444.777/0001-61",
        ]
        for cnpj in valid_cnpjs:
            result = validate_cnpj(cnpj)
            expected = cnpj.replace(".", "").replace("/", "").replace("-", "")
            assert result == expected, f"CNPJ {cnpj} should be valid"
    
    def test_invalid_cnpjs_wrong_digits(self):
        """Testa números de CNPJ com dígitos verificadores errados."""
        invalid_cnpjs = [
            "11222333000182",  # Wrong last digit
            "11222333000171",  # Wrong second-to-last digit
        ]
        for cnpj in invalid_cnpjs:
            assert validate_cnpj(cnpj) is False, f"CNPJ {cnpj} should be invalid"
    
    def test_invalid_cnpjs_wrong_length(self):
        """Testa números de CNPJ com comprimento errado."""
        invalid_cnpjs = [
            "1122233300018",   # Too short
            "112223330001811", # Too long
            "12345",           # Much too short
            "",                # Empty string
        ]
        for cnpj in invalid_cnpjs:
            assert validate_cnpj(cnpj) is False, f"CNPJ {cnpj} should be invalid"
    
    def test_cnpj_with_non_numeric_chars(self):
        """Testa CNPJ com caracteres não numéricos."""
        cnpj_with_letters = "11abc222def333ghi000jkl181"
        result = validate_cnpj(cnpj_with_letters)
        assert result == "11222333000181", "Should extract only digits and validate"


class TestValidatePlate:
    """Casos de teste para função de validação de placas de veículos."""
    
    def test_valid_old_format_plates(self):
        """Testa placas válidas no formato antigo (ABC1234)."""
        valid_plates = [
            "ABC1234",
            "XYZ9876",
            "AAA0000",
            "ZZZ9999",
        ]
        for plate in valid_plates:
            assert validate_plate(plate) is True, f"Plate {plate} should be valid"
    
    def test_valid_new_format_plates(self):
        """Testa placas válidas no formato novo (ABC1D23)."""
        valid_plates = [
            "ABC1D23",
            "XYZ2E45",
            "AAA0A00",
            "ZZZ9Z99",
        ]
        for plate in valid_plates:
            assert validate_plate(plate) is True, f"Plate {plate} should be valid"
    
    def test_valid_plates_lowercase(self):
        """Testa placas válidas em minúsculo (devem ser convertidas para maiúsculo)."""
        valid_plates = [
            "abc1234",
            "xyz1d23",
        ]
        for plate in valid_plates:
            assert validate_plate(plate) is True, f"Plate {plate} should be valid"
    
    def test_invalid_plates_wrong_length(self):
        """Testa placas com comprimento errado."""
        invalid_plates = [
            "ABC123",     # Too short
            "ABC12345",   # Too long
            "AB1234",     # Too short
            "",           # Empty string
        ]
        for plate in invalid_plates:
            assert validate_plate(plate) is False, f"Plate {plate} should be invalid"
    
    def test_invalid_plates_wrong_format(self):
        """Testa placas com formato de caracteres errado."""
        invalid_plates = [
            "1ABC234",    # Starts with number
            "A1C1234",    # Second char is number
            "AB11234",    # Third char is number
            "ABCD234",    # Fourth char is letter
            "ABC1234D",   # Extra character
            "ABC12D4",    # Wrong position for letter
        ]
        for plate in invalid_plates:
            assert validate_plate(plate) is False, f"Plate {plate} should be invalid"
    
    def test_invalid_plates_special_characters(self):
        """Testa placas com caracteres especiais."""
        invalid_plates = [
            "ABC-1234",
            "ABC 1234",
            "ABC@1234",
            "ABC#1D34",
        ]
        for plate in invalid_plates:
            assert validate_plate(plate) is False, f"Plate {plate} should be invalid"