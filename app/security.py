"""Palavras-passe (hash) e tokens JWT. Também tem as dependências de autenticação."""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import database

esquema = HTTPBearer(auto_error=False)


def _chave() -> str:
    # Em produção define SECRET_KEY; o valor por defeito serve só para desenvolvimento
    return os.getenv("SECRET_KEY", "dev-secret-change-me")


def hash_password(password: str) -> str:
    sal = os.urandom(16)
    hash_ = hashlib.pbkdf2_hmac("sha256", password.encode(), sal, 200_000)
    return sal.hex() + "$" + hash_.hex()


def verificar_password(password: str, guardado: str) -> bool:
    sal_hex, hash_hex = guardado.split("$")
    hash_ = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal_hex), 200_000)
    return hmac.compare_digest(hash_.hex(), hash_hex)


def criar_token(utilizador: dict) -> str:
    dados = {
        "sub": str(utilizador["id"]),
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(dados, _chave(), algorithm="HS256")


def utilizador_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(esquema)) -> dict:
    """Lê o cabeçalho 'Authorization: Bearer <token>' e devolve o utilizador."""
    if credenciais is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inicia sessão para continuar.")
    try:
        dados = jwt.decode(credenciais.credentials, _chave(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "A sessão expirou. Inicia sessão outra vez.")

    # O papel é lido da base de dados, não do token, para não ficar desatualizado
    utilizador = database.buscar_utilizador(int(dados["sub"]))
    if utilizador is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Conta não encontrada.")
    return utilizador


def exigir_admin(utilizador: dict = Depends(utilizador_atual)) -> dict:
    if utilizador["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Esta ação é só para administradores.")
    return utilizador
