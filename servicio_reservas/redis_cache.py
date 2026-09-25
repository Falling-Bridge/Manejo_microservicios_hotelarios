import json, os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
TTL = 30

_client = None


def _cli():
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL, decode_responses=True)
    return _client


def _k(fecha):
    return f"disp:{fecha}"


def get_disponibilidad(fecha):
    if not CACHE_ENABLED:
        return None
    try:
        raw = _cli().get(_k(fecha))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def set_disponibilidad(fecha, data):
    if not CACHE_ENABLED:
        return
    try:
        _cli().setex(_k(fecha), TTL, json.dumps(data))
    except Exception:
        pass


def invalidar(fecha):
    if not CACHE_ENABLED:
        return
    try:
        _cli().delete(_k(fecha))
    except Exception:
        pass