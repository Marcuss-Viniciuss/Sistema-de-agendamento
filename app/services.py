"""Regras de negócio. Não sabe nada de HTTP nem de SQL."""

import os
from datetime import date, datetime

from app import database, horarios
from app.exceptions import (
    AgendamentoNaoEncontradoError,
    CredenciaisInvalidasError,
    HorarioInvalidoError,
    HorarioNoPassadoError,
    HorarioOcupadoError,
)
from app.schemas import AgendamentoCreate
from app.security import hash_password, verificar_password


def criar_agendamento(dados: AgendamentoCreate, user_id: int | None = None) -> dict:
    # Regra 1: não se marca para o passado
    if dados.inicio < datetime.now():
        raise HorarioNoPassadoError()

    # Regra 2: só dias úteis, dentro do expediente e no início de um bloco
    if dados.inicio not in horarios.gerar_slots(dados.inicio.date()):
        raise HorarioInvalidoError(
            "Horário fora do expediente. Marcações de " + horarios.descricao_expediente() + "."
        )

    # Regra 3: um bloco só pode ter um agendamento.
    # Esta verificação serve para dar uma resposta rápida. A garantia real,
    # mesmo com pedidos em simultâneo, é o UNIQUE da coluna 'inicio' no banco:
    # se dois pedidos passarem aqui ao mesmo tempo, só um INSERT é aceite.
    if database.existe_horario(dados.inicio):
        raise HorarioOcupadoError()

    return database.inserir(dados.cliente, dados.servico, dados.inicio, user_id)


def listar_agendamentos(dia: date | None = None, user_id: int | None = None) -> list[dict]:
    return database.listar(dia, user_id)


def obter_agendamento(agendamento_id: int) -> dict:
    agendamento = database.buscar(agendamento_id)
    if agendamento is None:
        raise AgendamentoNaoEncontradoError()
    return agendamento


def cancelar_agendamento(agendamento_id: int) -> None:
    if not database.apagar(agendamento_id):
        raise AgendamentoNaoEncontradoError()


def atualizar_estado(agendamento_id: int, estado: str) -> dict:
    if not database.atualizar_estado(agendamento_id, estado):
        raise AgendamentoNaoEncontradoError()
    return database.buscar(agendamento_id)


# ---------- Contas ----------

def registar(nome: str, email: str, password: str) -> dict:
    # Quem se regista é sempre cliente; administradores vêm de garantir_admin()
    return database.criar_utilizador(nome, email, hash_password(password), "cliente")


def autenticar(email: str, password: str) -> dict:
    utilizador = database.buscar_utilizador_por_email(email)
    # A mesma mensagem para email e palavra-passe errados, para não revelar que contas existem
    if utilizador is None or not verificar_password(password, utilizador["password_hash"]):
        raise CredenciaisInvalidasError()
    return {k: utilizador[k] for k in ("id", "nome", "email", "role")}


def garantir_admin() -> None:
    """Cria a conta de administrador no arranque, se ainda não existir."""
    email = os.getenv("ADMIN_EMAIL", "admin@demo.pt")
    password = os.getenv("ADMIN_PASSWORD", "admin1234")
    if database.buscar_utilizador_por_email(email) is None:
        database.criar_utilizador("Administrador", email, hash_password(password), "admin")


def horarios_disponiveis(dia: date) -> dict:
    """Blocos do dia, menos os já ocupados e menos os que já passaram."""
    todos = horarios.gerar_slots(dia)
    ocupados = {a["inicio"] for a in database.listar(dia)}
    agora = datetime.now()
    livres = [s for s in todos if s not in ocupados and s > agora]
    return {
        "data": dia,
        "aberto": horarios.dia_util(dia),
        "duracao_minutos": horarios.duracao_slot(),
        "horarios": [s.strftime("%H:%M") for s in livres],
    }
