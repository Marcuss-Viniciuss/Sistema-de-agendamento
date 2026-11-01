"""Expediente, blocos, vagas livres e marcações em simultâneo."""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

import pytest

from app import horarios, services
from app.exceptions import HorarioInvalidoError, HorarioOcupadoError
from app.schemas import AgendamentoCreate

QUARTA = "2099-05-20"      # dia útil
SABADO = "2099-06-06"
LIVRES_NUM_DIA = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
]


def marcar(client, hora, dia=QUARTA):
    return client.post(
        "/agendamentos",
        json={"cliente": "João", "servico": "Corte", "inicio": f"{dia}T{hora}:00"},
    )


# ---------- Grelha de blocos (funções puras) ----------

def test_grelha_de_30_minutos_salta_o_almoco():
    slots = [s.strftime("%H:%M") for s in horarios.gerar_slots(date(2099, 5, 20))]

    assert slots == LIVRES_NUM_DIA


def test_grelha_de_60_minutos(monkeypatch):
    monkeypatch.setenv("SLOT_MINUTOS", "60")

    slots = [s.strftime("%H:%M") for s in horarios.gerar_slots(date(2099, 5, 20))]

    assert slots == ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00"]


def test_fim_de_semana_nao_tem_blocos():
    assert horarios.gerar_slots(date(2099, 6, 6)) == []   # sábado
    assert horarios.gerar_slots(date(2099, 6, 7)) == []   # domingo


# ---------- Regras ao marcar ----------

@pytest.mark.parametrize("hora", ["08:30", "12:00", "12:30", "18:00", "14:15"])
def test_recusa_fora_do_expediente_almoco_ou_fora_da_grelha(client, hora):
    resposta = marcar(client, hora)

    assert resposta.status_code == 422
    assert "expediente" in resposta.json()["detail"]


def test_recusa_fim_de_semana(client):
    assert marcar(client, "10:00", dia=SABADO).status_code == 422


@pytest.mark.parametrize("hora", ["09:00", "11:30", "13:00", "17:30"])
def test_aceita_primeiro_e_ultimo_bloco_de_cada_periodo(client, hora):
    assert marcar(client, hora).status_code == 201


# ---------- GET /horarios-disponiveis ----------

def test_dia_vazio_devolve_todos_os_blocos(client):
    r = client.get("/horarios-disponiveis", params={"data": QUARTA})

    assert r.status_code == 200
    assert r.json()["horarios"] == LIVRES_NUM_DIA
    assert r.json()["aberto"] is True
    assert r.json()["duracao_minutos"] == 30


def test_bloco_ocupado_sai_da_lista(client):
    marcar(client, "10:00")

    horas = client.get("/horarios-disponiveis", params={"data": QUARTA}).json()["horarios"]

    assert "10:00" not in horas
    assert len(horas) == len(LIVRES_NUM_DIA) - 1


def test_cancelar_devolve_o_bloco_a_lista(client):
    id_ = marcar(client, "10:00").json()["id"]
    client.delete(f"/agendamentos/{id_}")

    horas = client.get("/horarios-disponiveis", params={"data": QUARTA}).json()["horarios"]

    assert "10:00" in horas


def test_fim_de_semana_esta_fechado(client):
    r = client.get("/horarios-disponiveis", params={"data": SABADO}).json()

    assert r["aberto"] is False
    assert r["horarios"] == []


def test_dia_passado_nao_tem_vagas(client):
    r = client.get("/horarios-disponiveis", params={"data": "2000-01-03"}).json()

    assert r["horarios"] == []


def test_data_invalida_devolve_422(client):
    assert client.get("/horarios-disponiveis", params={"data": "2099-13-45"}).status_code == 422


def test_vagas_exigem_login(client_real):
    assert client_real.get("/horarios-disponiveis", params={"data": QUARTA}).status_code == 401


# ---------- Race condition ----------

def test_marcacoes_simultaneas_no_mesmo_bloco_so_uma_passa(banco):
    total = 8
    arranque = threading.Barrier(total)   # todos os pedidos começam ao mesmo tempo

    def tentar(i):
        dados = AgendamentoCreate(
            cliente=f"Cliente {i}", servico="Corte", inicio=datetime(2099, 5, 20, 10, 0)
        )
        arranque.wait()
        try:
            services.criar_agendamento(dados)
            return "ok"
        except HorarioOcupadoError:
            return "ocupado"

    with ThreadPoolExecutor(max_workers=total) as pool:
        resultados = list(pool.map(tentar, range(total)))

    assert resultados.count("ok") == 1
    assert resultados.count("ocupado") == total - 1
    assert len(services.listar_agendamentos()) == 1
