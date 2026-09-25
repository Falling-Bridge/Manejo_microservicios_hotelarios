import json
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.responses import JSONResponse

from auth import verificar_api_key
from db import get_conn, init_db
from models import HuespedCreate, HuespedOut, ReservaCreate, ReservaOut
import grpc_client
import redis_cache

app = FastAPI(
    title="API de Reservas - Cadena Hotelera Costanera",
    version="1.0.0",
    description="API REST pública. Disponibilidad vía gRPC a Habitaciones.",
)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


# Huespedes
@app.post("/v1/huespedes", response_model=HuespedOut,
         status_code=status.HTTP_201_CREATED,
         dependencies=[Depends(verificar_api_key)], tags=["huespedes"])
def crear_huesped(body: HuespedCreate):
    hid = str(uuid.uuid4())
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO huespedes (id, nombre, email, telefono) VALUES (?, ?, ?, ?)",
                (hid, body.nombre, body.email, body.telefono))
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(409, "Email ya registrado")
        raise HTTPException(500, str(e))
    return HuespedOut(id=hid, nombre=body.nombre, email=body.email, telefono=body.telefono)


@app.get("/v1/huespedes/{hid}", response_model=HuespedOut,
         dependencies=[Depends(verificar_api_key)], tags=["huespedes"])
def obtener_huesped(hid: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM huespedes WHERE id = ?", (hid,)).fetchone()
    if not row:
        raise HTTPException(404, "Huésped no encontrado")
    return HuespedOut(**dict(row))


@app.get("/v1/huespedes", response_model=list[HuespedOut],
         dependencies=[Depends(verificar_api_key)], tags=["huespedes"])
def listar_huespedes():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM huespedes ORDER BY nombre").fetchall()
    return [HuespedOut(**dict(r)) for r in rows]


# Disponibilidad
@app.get("/v1/disponibilidad/{fecha}",
         dependencies=[Depends(verificar_api_key)], tags=["disponibilidad"])
def disponibilidad(fecha: str):
    cached = redis_cache.get_disponibilidad(fecha)
    if cached is not None:
        return cached
    try:
        data = grpc_client.consultar_disponibilidad(fecha)
    except grpc_client.HabitacionesUnavailable:
        raise HTTPException(503,
            "Servicio de Habitaciones no disponible. Reintente en unos segundos.",
            headers={"Retry-After": "5"})
    redis_cache.set_disponibilidad(fecha, data)
    return data


# Reservas
@app.post("/v1/reservas", response_model=ReservaOut,
         status_code=status.HTTP_201_CREATED,
         dependencies=[Depends(verificar_api_key)], tags=["reservas"])
def crear_reserva(body: ReservaCreate, idempotency_key: str | None = Header(default=None)):
    if idempotency_key:
        with get_conn() as conn:
            row = conn.execute("SELECT respuesta FROM idempotency WHERE key = ?",
                               (idempotency_key,)).fetchone()
        if row:
            return JSONResponse(status_code=201, content=json.loads(row["respuesta"]))

    with get_conn() as conn:
        h = conn.execute("SELECT id FROM huespedes WHERE id = ?", (body.huesped_id,)).fetchone()
    if not h:
        raise HTTPException(404, "Huésped no encontrado")

    try:
        disp = grpc_client.consultar_disponibilidad(body.fecha)
    except grpc_client.HabitacionesUnavailable:
        raise HTTPException(503, "Habitaciones no disponible",
                            headers={"Retry-After": "5"})
    if disp["habitaciones_libres"] <= 0:
        raise HTTPException(409, "Sin habitaciones disponibles para esa fecha")

    rid = str(uuid.uuid4())
    creada = datetime.now(timezone.utc).isoformat()
    try:
        op = grpc_client.reservar_habitacion(body.fecha, rid)
    except grpc_client.HabitacionesUnavailable:
        raise HTTPException(503, "Habitaciones no disponible al confirmar",
                            headers={"Retry-After": "5"})
    if not op["ok"]:
        raise HTTPException(409, op["mensaje"])

    payload = {"id": rid, "huesped_id": body.huesped_id, "fecha": body.fecha,
               "estado": "activa", "habitacion_id": op["habitacion_id"],
               "creada_en": creada}
    with get_conn() as conn:
        conn.execute("""INSERT INTO reservas
            (id, huesped_id, fecha, estado, habitacion_id, creada_en)
            VALUES (?, ?, ?, 'activa', ?, ?)""",
            (rid, body.huesped_id, body.fecha, op["habitacion_id"], creada))
        if idempotency_key:
            conn.execute("INSERT INTO idempotency (key, respuesta, creada_en) VALUES (?, ?, ?)",
                         (idempotency_key, json.dumps(payload), creada))

    redis_cache.invalidar(body.fecha)
    return ReservaOut(**payload)


@app.delete("/v1/reservas/{rid}",
            dependencies=[Depends(verificar_api_key)], tags=["reservas"])
def revertir_reserva(rid: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM reservas WHERE id = ?", (rid,)).fetchone()
    if not row:
        raise HTTPException(404, "Reserva no encontrada")
    if row["estado"] == "revertida":
        raise HTTPException(409, "Ya estaba revertida")

    try:
        op = grpc_client.liberar_habitacion(row["fecha"], rid)
    except grpc_client.HabitacionesUnavailable:
        raise HTTPException(503, "Habitaciones no disponible para revertir",
                            headers={"Retry-After": "5"})

    with get_conn() as conn:
        conn.execute("UPDATE reservas SET estado = 'revertida' WHERE id = ?", (rid,))
    redis_cache.invalidar(row["fecha"])
    return {"id": rid, "estado": "revertida", "liberada": op["ok"], "mensaje": op["mensaje"]}


@app.get("/v1/reservas/{rid}", response_model=ReservaOut,
         dependencies=[Depends(verificar_api_key)], tags=["reservas"])
def obtener_reserva(rid: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM reservas WHERE id = ?", (rid,)).fetchone()
    if not row:
        raise HTTPException(404, "Reserva no encontrada")
    return ReservaOut(**dict(row))


@app.get("/v1/reservas", response_model=list[ReservaOut],
         dependencies=[Depends(verificar_api_key)], tags=["reservas"])
def listar_reservas():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM reservas ORDER BY creada_en DESC").fetchall()
    return [ReservaOut(**dict(r)) for r in rows]