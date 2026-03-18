from enum import Enum


class TicketStatus(str, Enum):
    PENDENTE = "PENDENTE"
    RESTRITO = "RESTRITO"
    BLOQUEADO = "BLOQUEADO"
    AGUARDANDO_REVISAO = "AGUARDANDO_REVISAO",
    CONCLUIDO = "CONCLUIDO"

class TicketPriority(str, Enum):
    URGENTE = "URGENTE"
    ALTA = "ALTA"
    ROTINA = "ROTINA"

class UserRoleEnum(str, Enum):
    COORDENADOR = "Coordenador"
    ADMINISTRATIVO = "Administrativo"
    ADJUNTO = "Adjunto"
    LIDER_DE_ILHA = "Líder de Ilha"
    OPERADOR = "Operador"
