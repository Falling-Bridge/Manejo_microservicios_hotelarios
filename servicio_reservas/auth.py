import os
from fastapi import Header, HTTPException

API_KEY = os.getenv("API_KEY", "clave-demo-123")


def verificar_api_key(x_api_key: str | None = Header(default=None)):
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="API Key inválida o ausente",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    return True