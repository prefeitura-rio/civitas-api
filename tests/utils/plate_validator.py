"""
Módulo centralizado para validação de placas brasileiras.
"""
import re


def validate_plate(plate: str) -> bool:
    """
    Valida placas brasileiras nos formatos antigo e Mercosul.
    
    Formatos aceitos:
    - Antigo: ABC1234 (3 letras + 4 dígitos)
    - Mercosul: ABC1D23 (3 letras + 1 dígito + 1 letra + 2 dígitos)
    
    Args:
        plate: String da placa a ser validada
        
    Returns:
        bool: True se válida, False caso contrário
    """
    if not plate or not isinstance(plate, str):
        return False
    
    plate = plate.upper().strip()
    
    if len(plate) != 7:
        return False
    
    # Padrão brasileiro: 3 letras + 1 dígito + (1 letra ou 1 dígito) + 2 dígitos
    pattern = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
    return pattern.match(plate) is not None


def normalize_plate(plate: str) -> str:
    """
    Normaliza a placa removendo espaços e convertendo para maiúscula.
    
    Args:
        plate: String da placa
        
    Returns:
        str: Placa normalizada
    """
    if not plate or not isinstance(plate, str):
        return ""
    
    return plate.upper().strip()


def get_plate_format(plate: str) -> str:
    """
    Identifica o formato da placa.
    
    Args:
        plate: String da placa
        
    Returns:
        str: "mercosul", "antigo" ou "invalido"
    """
    if not validate_plate(plate):
        return "invalido"
    
    normalized = normalize_plate(plate)
    
    # Posição 4 (índice 4) determina o formato
    if normalized[4].isdigit():
        return "antigo"  # ABC1234
    else:
        return "mercosul"  # ABC1D23