"""Autenticação e permissões por papel, sem atalhos."""

FUTURO = "2099-05-20T{}:00:00"


def registar(c, nome, email):
    r = c.post("/auth/registo", json={"nome": nome, "email": email, "password": "segredo123"})
    return r.json()["access_token"]


def entrar_admin(c):
    r = c.post("/auth/login", json={"email": "admin@teste.pt", "password": "admin-teste-1"})
    return r.json()["access_token"]


def h(token):
    return {"Authorization": f"Bearer {token}"}


def marcar(c, token, hora, cliente=None):
    corpo = {"servico": "Corte", "inicio": FUTURO.format(hora)}
    if cliente:
        corpo["cliente"] = cliente
    return c.post("/agendamentos", json=corpo, headers=h(token))


def test_registo_cria_cliente_e_devolve_token(client_real):
    r = client_real.post("/auth/registo", json={"nome": "Ana", "email": "Ana@Mail.pt", "password": "segredo123"})

    assert r.status_code == 201
    assert r.json()["utilizador"]["role"] == "cliente"
    assert r.json()["utilizador"]["email"] == "ana@mail.pt"


def test_email_repetido_devolve_409(client_real):
    registar(client_real, "Ana", "ana@mail.pt")

    r = client_real.post("/auth/registo", json={"nome": "Outra", "email": "ana@mail.pt", "password": "segredo123"})

    assert r.status_code == 409


def test_login_com_password_errada_devolve_401(client_real):
    registar(client_real, "Ana", "ana@mail.pt")

    r = client_real.post("/auth/login", json={"email": "ana@mail.pt", "password": "errada"})

    assert r.status_code == 401


def test_sem_token_devolve_401(client_real):
    assert client_real.get("/agendamentos").status_code == 401


def test_token_invalido_devolve_401(client_real):
    assert client_real.get("/agendamentos", headers=h("lixo")).status_code == 401


def test_cliente_usa_sempre_o_proprio_nome(client_real):
    token = registar(client_real, "Ana", "ana@mail.pt")

    r = marcar(client_real, token, "10", cliente="Outra Pessoa")

    assert r.status_code == 201
    assert r.json()["cliente"] == "Ana"


def test_cliente_so_ve_os_seus_e_admin_ve_todos(client_real):
    ana = registar(client_real, "Ana", "ana@mail.pt")
    bruno = registar(client_real, "Bruno", "bruno@mail.pt")
    admin = entrar_admin(client_real)
    marcar(client_real, ana, "10")
    marcar(client_real, bruno, "11")
    marcar(client_real, admin, "14", cliente="Cliente de balcão")

    assert len(client_real.get("/agendamentos", headers=h(ana)).json()) == 1
    assert len(client_real.get("/agendamentos", headers=h(admin)).json()) == 3


def test_cliente_nao_ve_agendamento_de_outro(client_real):
    ana = registar(client_real, "Ana", "ana@mail.pt")
    bruno = registar(client_real, "Bruno", "bruno@mail.pt")
    id_ana = marcar(client_real, ana, "10").json()["id"]

    assert client_real.get(f"/agendamentos/{id_ana}", headers=h(bruno)).status_code == 404


def test_cliente_nao_apaga_mas_admin_apaga(client_real):
    ana = registar(client_real, "Ana", "ana@mail.pt")
    admin = entrar_admin(client_real)
    id_ana = marcar(client_real, ana, "10").json()["id"]

    assert client_real.delete(f"/agendamentos/{id_ana}", headers=h(ana)).status_code == 403
    assert client_real.delete(f"/agendamentos/{id_ana}", headers=h(admin)).status_code == 204


def test_so_admin_conclui_agendamentos(client_real):
    ana = registar(client_real, "Ana", "ana@mail.pt")
    admin = entrar_admin(client_real)
    id_ana = marcar(client_real, ana, "10").json()["id"]
    corpo = {"estado": "concluido"}

    assert client_real.patch(f"/agendamentos/{id_ana}", json=corpo, headers=h(ana)).status_code == 403
    r = client_real.patch(f"/agendamentos/{id_ana}", json=corpo, headers=h(admin))
    assert r.status_code == 200
    assert r.json()["estado"] == "concluido"


def test_admin_tem_de_indicar_o_cliente(client_real):
    admin = entrar_admin(client_real)

    assert marcar(client_real, admin, "10").status_code == 422
