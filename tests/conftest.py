import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.security import utilizador_atual

ADMIN_FALSO = {"id": 0, "nome": "Admin Teste", "email": "admin@teste.pt", "role": "admin"}


@pytest.fixture
def banco(tmp_path, monkeypatch):
    """Base de dados temporária e vazia para cada teste."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setenv("ADMIN_EMAIL", "admin@teste.pt")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin-teste-1")
    init_db()


@pytest.fixture
def client(banco):
    # Atalho: pedidos já autenticados como admin, para testar a API sem repetir logins
    app.dependency_overrides[utilizador_atual] = lambda: ADMIN_FALSO
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_real(banco):
    # Sem atalhos: a autenticação corre a sério
    with TestClient(app) as c:
        yield c
