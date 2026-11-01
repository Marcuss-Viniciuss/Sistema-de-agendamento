"""Testes da regra de negócio, sem passar pela API."""

from datetime import datetime

import pytest

from app import services
from app.exceptions import (
    AgendamentoNaoEncontradoError,
    HorarioNoPassadoError,
    HorarioOcupadoError,
)
from app.schemas import AgendamentoCreate

FUTURO = datetime(2099, 6, 1, 14, 30)


def novo(cliente="Ana", inicio=FUTURO):
    return AgendamentoCreate(cliente=cliente, servico="Corte", inicio=inicio)


def test_bloqueia_horario_duplicado(banco):
    services.criar_agendamento(novo("Ana"))

    with pytest.raises(HorarioOcupadoError):
        services.criar_agendamento(novo("Bruno"))


def test_segundos_diferentes_contam_como_mesmo_horario(banco):
    services.criar_agendamento(novo("Ana", datetime(2099, 6, 1, 14, 30, 0)))

    with pytest.raises(HorarioOcupadoError):
        services.criar_agendamento(novo("Bruno", datetime(2099, 6, 1, 14, 30, 45)))


def test_permite_mesma_hora_em_dias_diferentes(banco):
    services.criar_agendamento(novo(inicio=datetime(2099, 6, 1, 14, 30)))
    services.criar_agendamento(novo(inicio=datetime(2099, 6, 2, 14, 30)))

    assert len(services.listar_agendamentos()) == 2


def test_recusa_data_no_passado(banco):
    with pytest.raises(HorarioNoPassadoError):
        services.criar_agendamento(novo(inicio=datetime(2000, 1, 1, 10, 0)))


def test_cancelar_inexistente_da_erro(banco):
    with pytest.raises(AgendamentoNaoEncontradoError):
        services.cancelar_agendamento(999)
