"""Rotas HTTP. Só traduz pedidos/respostas e erros de negócio em códigos HTTP."""

import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import services
from app.database import init_db
from app.exceptions import (
    AgendamentoNaoEncontradoError,
    CredenciaisInvalidasError,
    EmailJaExisteError,
    HorarioInvalidoError,
    HorarioNoPassadoError,
    HorarioOcupadoError,
)
from app.schemas import (
    AgendamentoCreate,
    AgendamentoOut,
    EstadoIn,
    HorariosOut,
    LoginIn,
    RegistoIn,
    TokenOut,
    UtilizadorOut,
)
from app.security import criar_token, exigir_admin, utilizador_atual


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Corre uma vez no arranque: garante que a tabela existe
    init_db()
    services.garantir_admin()
    yield


app = FastAPI(
    title="API de Agendamentos",
    description="Gestão simples de marcações para uma barbearia.",
    version="1.0.0",
    lifespan=lifespan,
)


# CORS: permite que o frontend (outra porta) chame a API a partir do navegador.
# Por defeito aceita o servidor estático local na porta 5500; podes mudar
# com a variável CORS_ORIGINS (endereços separados por vírgulas).
origens = os.getenv(
    "CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origens,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(sqlite3.Error)
async def tratar_erro_banco(request: Request, exc: sqlite3.Error):
    # Qualquer falha inesperada do banco vira uma resposta 500 limpa,
    # sem expor detalhes internos ao cliente.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno ao aceder à base de dados."},
    )


@app.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok"}


@app.post("/auth/registo", response_model=TokenOut, status_code=status.HTTP_201_CREATED, tags=["Autenticação"])
def registo(dados: RegistoIn):
    try:
        utilizador = services.registar(dados.nome, dados.email, dados.password)
    except EmailJaExisteError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com este email.")
    return {"access_token": criar_token(utilizador), "utilizador": utilizador}


@app.post("/auth/login", response_model=TokenOut, tags=["Autenticação"])
def login(dados: LoginIn):
    try:
        utilizador = services.autenticar(dados.email, dados.password)
    except CredenciaisInvalidasError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou palavra-passe incorretos.")
    return {"access_token": criar_token(utilizador), "utilizador": utilizador}


@app.get("/auth/me", response_model=UtilizadorOut, tags=["Autenticação"])
def eu(utilizador: dict = Depends(utilizador_atual)):
    return utilizador


@app.post(
    "/agendamentos",
    response_model=AgendamentoOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Agendamentos"],
)
def criar(dados: AgendamentoCreate, utilizador: dict = Depends(utilizador_atual)):
    if utilizador["role"] == "admin":
        # O admin marca em nome de um cliente (ex: alguém que ligou ou apareceu)
        if not dados.cliente:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indica o nome do cliente.")
        dono = None
    else:
        # O cliente só marca para si próprio, qualquer nome enviado é ignorado
        dados.cliente = utilizador["nome"]
        dono = utilizador["id"]
    try:
        return services.criar_agendamento(dados, dono)
    except HorarioNoPassadoError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Não é possível marcar no passado.")
    except HorarioInvalidoError as erro:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(erro))
    except HorarioOcupadoError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esse horário já está ocupado.")


@app.get("/horarios-disponiveis", response_model=HorariosOut, tags=["Agendamentos"])
def horarios_disponiveis(data: date, utilizador: dict = Depends(utilizador_atual)):
    """Horas ainda livres num dia (`?data=AAAA-MM-DD`). Vazio ao fim de semana ou em dias passados."""
    return services.horarios_disponiveis(data)


@app.get("/agendamentos", response_model=list[AgendamentoOut], tags=["Agendamentos"])
def listar(data: date | None = None, utilizador: dict = Depends(utilizador_atual)):
    """Admin vê tudo; cliente vê só os seus. `?data=AAAA-MM-DD` filtra por dia."""
    dono = None if utilizador["role"] == "admin" else utilizador["id"]
    return services.listar_agendamentos(data, dono)


@app.get("/agendamentos/{agendamento_id}", response_model=AgendamentoOut, tags=["Agendamentos"])
def obter(agendamento_id: int, utilizador: dict = Depends(utilizador_atual)):
    try:
        agendamento = services.obter_agendamento(agendamento_id)
    except AgendamentoNaoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agendamento não encontrado.")
    # Para um cliente, o agendamento de outra pessoa é tratado como inexistente
    if utilizador["role"] != "admin" and agendamento["user_id"] != utilizador["id"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agendamento não encontrado.")
    return agendamento


@app.patch(
    "/agendamentos/{agendamento_id}",
    response_model=AgendamentoOut,
    tags=["Agendamentos"],
    dependencies=[Depends(exigir_admin)],
)
def atualizar_estado(agendamento_id: int, corpo: EstadoIn):
    try:
        return services.atualizar_estado(agendamento_id, corpo.estado)
    except AgendamentoNaoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agendamento não encontrado.")


@app.delete(
    "/agendamentos/{agendamento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Agendamentos"],
    dependencies=[Depends(exigir_admin)],
)
def cancelar(agendamento_id: int):
    try:
        services.cancelar_agendamento(agendamento_id)
    except AgendamentoNaoEncontradoError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agendamento não encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
