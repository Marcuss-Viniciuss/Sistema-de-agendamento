"""Erros de negócio da aplicação.

Ficam num ficheiro à parte para a camada de dados e a camada de serviço
poderem usá-los sem importarem uma à outra (evita imports circulares).
A tradução para códigos HTTP é feita só em main.py.
"""


class HorarioOcupadoError(Exception):
    """Já existe um agendamento nesse dia e hora."""


class HorarioNoPassadoError(Exception):
    """Tentativa de marcar para uma data/hora que já passou."""


class AgendamentoNaoEncontradoError(Exception):
    """Não existe agendamento com o ID pedido."""


class EmailJaExisteError(Exception):
    """Já existe uma conta com este email."""


class CredenciaisInvalidasError(Exception):
    """Email ou palavra-passe errados."""


class HorarioInvalidoError(Exception):
    """Fim de semana, fora do expediente, na pausa de almoço ou fora da grelha de blocos."""
