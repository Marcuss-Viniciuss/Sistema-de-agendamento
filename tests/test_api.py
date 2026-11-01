"""Testes ponta a ponta: pedidos HTTP reais contra a aplicação."""

import sqlite3

from app import services

BASE = {"cliente": "João", "servico": "Corte", "inicio": "2099-05-20T14:30:00"}


def test_criar_agendamento(client):
    resposta = client.post("/agendamentos", json=BASE)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["cliente"] == "João"
    assert corpo["inicio"] == "2099-05-20T14:30:00"


def test_horario_duplicado_devolve_409(client):
    client.post("/agendamentos", json=BASE)

    resposta = client.post("/agendamentos", json={**BASE, "cliente": "Maria"})

    assert resposta.status_code == 409


def test_data_inexistente_devolve_422(client):
    resposta = client.post("/agendamentos", json={**BASE, "inicio": "2099-13-45T10:00:00"})

    assert resposta.status_code == 422


def test_cliente_vazio_devolve_422(client):
    resposta = client.post("/agendamentos", json={**BASE, "cliente": "   "})

    assert resposta.status_code == 422


def test_data_no_passado_devolve_422(client):
    resposta = client.post("/agendamentos", json={**BASE, "inicio": "2000-01-01T10:00:00"})

    assert resposta.status_code == 422


def test_listagem_vem_por_ordem_cronologica(client):
    # Inseridos fora de ordem de propósito (o problema do DD/MM/AAAA do script antigo)
    client.post("/agendamentos", json={**BASE, "inicio": "2099-12-01T09:00:00"})
    client.post("/agendamentos", json={**BASE, "inicio": "2099-02-16T10:00:00"})
    client.post("/agendamentos", json={**BASE, "inicio": "2099-02-16T09:00:00"})

    datas = [a["inicio"] for a in client.get("/agendamentos").json()]

    assert datas == [
        "2099-02-16T09:00:00",
        "2099-02-16T10:00:00",
        "2099-12-01T09:00:00",
    ]


def test_filtrar_por_dia(client):
    client.post("/agendamentos", json={**BASE, "inicio": "2099-02-16T09:00:00"})
    client.post("/agendamentos", json={**BASE, "inicio": "2099-02-17T09:00:00"})

    resposta = client.get("/agendamentos", params={"data": "2099-02-17"})

    assert len(resposta.json()) == 1


def test_obter_inexistente_devolve_404(client):
    assert client.get("/agendamentos/999").status_code == 404


def test_cancelar_e_libertar_horario(client):
    criado = client.post("/agendamentos", json=BASE).json()

    assert client.delete(f"/agendamentos/{criado['id']}").status_code == 204
    assert client.get(f"/agendamentos/{criado['id']}").status_code == 404
    # O horário ficou livre outra vez
    assert client.post("/agendamentos", json=BASE).status_code == 201


def test_cancelar_inexistente_devolve_404(client):
    assert client.delete("/agendamentos/999").status_code == 404


def test_erro_de_banco_devolve_500_limpo(client, monkeypatch):
    def falha(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(services, "listar_agendamentos", falha)

    resposta = client.get("/agendamentos")

    assert resposta.status_code == 500
    assert "locked" not in resposta.text  # não expõe detalhes internos
