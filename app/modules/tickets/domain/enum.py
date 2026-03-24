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