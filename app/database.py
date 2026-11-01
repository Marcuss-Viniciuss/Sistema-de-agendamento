"""Acesso ao SQLite: ligação, criação da tabela e queries.

Todo o SQL vive aqui. O resto da aplicação não sabe que existe SQLite,
só chama estas funções.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

from app.exceptions import EmailJaExisteError, HorarioOcupadoError


def caminho_bd() -> str:
    # Lido a cada chamada (e não ao importar) para os testes poderem
    # apontar para uma base de dados temporária.
    return os.getenv("DATABASE_PATH", "agendamentos.db")


@contextmanager
def conectar():
    """Abre uma ligação, faz commit se correr bem, rollback se falhar, e fecha sempre."""
    conexao = sqlite3.connect(caminho_bd(), timeout=10)
    conexao.row_factory = sqlite3.Row
    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def init_db() -> None:
    """Cria a pasta e a tabela, se ainda não existirem."""
    pasta = os.path.dirname(caminho_bd())
    if pasta:
        os.makedirs(pasta, exist_ok=True)

    with conectar() as conexao:
        # 'inicio' guarda "AAAA-MM-DD HH:MM". Neste formato, ordenar por texto
        # é o mesmo que ordenar por data. O UNIQUE é a rede de segurança que
        # garante, no próprio banco, que não há dois agendamentos no mesmo horário.
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS agendamentos (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente TEXT NOT NULL,
                servico TEXT NOT NULL,
                inicio  TEXT NOT NULL UNIQUE,
                user_id INTEGER,
                estado  TEXT NOT NULL DEFAULT 'pendente'
            )
            """
        )
        # Bases criadas na versão anterior não têm as colunas novas
        colunas = [c["name"] for c in conexao.execute("PRAGMA table_info(agendamentos)")]
        if "user_id" not in colunas:
            conexao.execute("ALTER TABLE agendamentos ADD COLUMN user_id INTEGER")
        if "estado" not in colunas:
            conexao.execute("ALTER TABLE agendamentos ADD COLUMN estado TEXT NOT NULL DEFAULT 'pendente'")

        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS utilizadores (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                nome          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'cliente'
            )
            """
        )


def _para_texto(inicio: datetime) -> str:
    return inicio.isoformat(sep=" ", timespec="minutes")


def _para_dict(linha: sqlite3.Row) -> dict:
    return {
        "id": linha["id"],
        "cliente": linha["cliente"],
        "servico": linha["servico"],
        "inicio": datetime.fromisoformat(linha["inicio"]),
        "estado": linha["estado"],
        "user_id": linha["user_id"],
    }


def existe_horario(inicio: datetime) -> bool:
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT 1 FROM agendamentos WHERE inicio = ?", (_para_texto(inicio),)
        ).fetchone()
    return linha is not None


def inserir(cliente: str, servico: str, inicio: datetime, user_id: int | None = None) -> dict:
    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                "INSERT INTO agendamentos (cliente, servico, inicio, user_id) VALUES (?, ?, ?, ?)",
                (cliente, servico, _para_texto(inicio), user_id),
            )
            novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        # Dois pedidos simultâneos podem passar pela verificação prévia;
        # o UNIQUE apanha o segundo.
        raise HorarioOcupadoError()
    return {
        "id": novo_id, "cliente": cliente, "servico": servico,
        "inicio": inicio, "estado": "pendente", "user_id": user_id,
    }


def listar(dia: date | None = None, user_id: int | None = None) -> list[dict]:
    # Monta o WHERE só com os filtros que foram pedidos
    condicoes = []
    valores = []
    if dia is not None:
        condicoes.append("date(inicio) = ?")
        valores.append(dia.isoformat())
    if user_id is not None:
        condicoes.append("user_id = ?")
        valores.append(user_id)
    where = " WHERE " + " AND ".join(condicoes) if condicoes else ""

    with conectar() as conexao:
        linhas = conexao.execute(
            "SELECT * FROM agendamentos" + where + " ORDER BY inicio", valores
        ).fetchall()
    return [_para_dict(linha) for linha in linhas]


def buscar(agendamento_id: int) -> dict | None:
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT * FROM agendamentos WHERE id = ?", (agendamento_id,)
        ).fetchone()
    return _para_dict(linha) if linha else None


def apagar(agendamento_id: int) -> bool:
    """Devolve True se apagou alguma linha, False se o ID não existia."""
    with conectar() as conexao:
        cursor = conexao.execute(
            "DELETE FROM agendamentos WHERE id = ?", (agendamento_id,)
        )
        return cursor.rowcount > 0


def atualizar_estado(agendamento_id: int, estado: str) -> bool:
    with conectar() as conexao:
        cursor = conexao.execute(
            "UPDATE agendamentos SET estado = ? WHERE id = ?", (estado, agendamento_id)
        )
        return cursor.rowcount > 0


# ---------- Utilizadores ----------

def criar_utilizador(nome: str, email: str, password_hash: str, role: str = "cliente") -> dict:
    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                "INSERT INTO utilizadores (nome, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (nome, email, password_hash, role),
            )
            novo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        raise EmailJaExisteError()
    return {"id": novo_id, "nome": nome, "email": email, "role": role}


def buscar_utilizador_por_email(email: str) -> dict | None:
    """Inclui password_hash: usar só para verificar o login."""
    with conectar() as conexao:
        linha = conexao.execute("SELECT * FROM utilizadores WHERE email = ?", (email,)).fetchone()
    return dict(linha) if linha else None


def buscar_utilizador(utilizador_id: int) -> dict | None:
    with conectar() as conexao:
        linha = conexao.execute(
            "SELECT id, nome, email, role FROM utilizadores WHERE id = ?", (utilizador_id,)
        ).fetchone()
    return dict(linha) if linha else None
