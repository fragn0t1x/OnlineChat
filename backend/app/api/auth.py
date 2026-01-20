# backend/app/api/auth.py
import os  # ← добавьте этот импорт
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

OPERATOR_API_KEYS = set(os.getenv("OPERATOR_API_KEYS", "").split(","))

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_operator(api_key: str = Depends(api_key_header)):
    if api_key not in OPERATOR_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    return api_key