"""Modelos Pydantic: definem e validam o que entra e sai da API."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgendamentoCreate(BaseModel):
    """Corpo do pedido POST /agendamentos."""

    # Remove espaços no início/fim antes de validar, por isso "   " fica vazio -> 422
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "cliente": "João Silva",
                "servico": "Corte de cabelo",
                "inicio": "2030-05-20T14:30:00",
            }
        },
    )

    # Opcional: o cliente autenticado é preenchido pela API; só o admin envia um nome
    cliente: str | None = Field(default=None, min_length=1, max_length=100)
    servico: str = Field(min_length=1, max_length=100)
    inicio: datetime

    @field_validator("inicio")
    @classmethod
    def normalizar_inicio(cls, valor: datetime) -> datetime:
        # Guardamos tudo sem fuso horário e sem segundos, para que
        # 14:30:00 e 14:30:45 sejam tratados como o mesmo horário.
        if valor.tzinfo is not None:
            raise ValueError("Envia a data/hora sem fuso horário (ex: 2030-05-20T14:30:00)")
        return valor.replace(second=0, microsecond=0)


class AgendamentoOut(BaseModel):
    """Formato devolvido pela API."""

    id: int
    cliente: str
    servico: str
    inicio: datetime
    estado: str


EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegistoIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nome: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=EMAIL_REGEX, max_length=120)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def email_minusculas(cls, valor: str) -> str:
        return valor.lower()


class LoginIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_minusculas(cls, valor: str) -> str:
        return valor.lower()


class UtilizadorOut(BaseModel):
    id: int
    nome: str
    email: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    utilizador: UtilizadorOut


class EstadoIn(BaseModel):
    estado: Literal["pendente", "concluido"]


class HorariosOut(BaseModel):
    data: date
    aberto: bool            # False ao fim de semana
    duracao_minutos: int
    horarios: list[str]     # só as horas ainda livres, ex: ["09:00", "09:30"]
