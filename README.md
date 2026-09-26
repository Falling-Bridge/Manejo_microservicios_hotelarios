# Manejo de Microservicios Hoteleros

Sistema de integración entre los microservicios de **Habitaciones** (gRPC, interno)
y **Reservas** (REST, público) de la Cadena Hotelera Costanera. Resuelve el
problema de overbooking causado por la falta de integración entre ambos sistemas.

- **Dominio:** Sistema de Gestión de Hotelería (Forma H)
- **Curso:** Integración de Sistemas — Unidad 1
- **Universidad de Concepción — Facultad de Ingeniería**
- **Docente:** Gonzalo Pérez Correa
- **Integrante:** Lucas Morales Oyanedel

---

## Tabla de contenidos

- [Arquitectura](#arquitectura)
- [Requisitos previos](#requisitos-previos)
- [Cómo levantar el sistema](#cómo-levantar-el-sistema)
- [Endpoints principales](#endpoints-principales)
- [Modo de falla](#modo-de-falla)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Reproducir el experimento](#reproducir-el-experimento)
- [Regenerar el contrato OpenAPI](#regenerar-el-contrato-openapi)
- [Bajar el sistema](#bajar-el-sistema)
- [Decisiones de arquitectura (ADRs)](#decisiones-de-arquitectura-adrs)
- [Declaración de uso de asistentes de IA](#declaración-de-uso-de-asistentes-de-ia)
- [Video de la solución](#video-de-la-solución)

---

## Arquitectura

```
┌──────────────────────────────────────────────────┐
│           Cliente externo                        │
│    (navegador, curl, portal web futuro)          │
└──────────────────────┬───────────────────────────┘
                       │ HTTP + JSON + X-API-Key
                       ▼
┌──────────────────────────────────────────────────┐
│        SERVICIO RESERVAS (:8000)                 │
│           FastAPI + Uvicorn                      │
│  ┌────────────────────────────────────────────┐  │
│  │  Endpoints /v1:                            │  │
│  │   • POST   /huespedes                      │  │
│  │   • GET    /huespedes                      │  │
│  │   • GET    /huespedes/{id}                 │  │
│  │   • GET    /disponibilidad/{fecha}         │  │
│  │   • POST   /reservas    (Idempotency-Key)  │  │
│  │   • GET    /reservas                       │  │
│  │   • GET    /reservas/{id}                  │  │
│  │   • DELETE /reservas/{id}                  │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  SQLite: reservas.db        Caché: Redis (:6379) │
└──────────────────────┬───────────────────────────┘
                       │ gRPC + Protobuf
                       │ timeout 500 ms
                       ▼
┌──────────────────────────────────────────────────┐
│      SERVICIO HABITACIONES (:50051)              │
│              gRPC (grpcio)                       │
│  ┌────────────────────────────────────────────┐  │
│  │  RPCs:                                     │  │
│  │   • ConsultarDisponibilidad(fecha)         │  │
│  │   • ListarDisponibilidad(rango)            │  │
│  │   • ReservarHabitacion(fecha, reserva_id)  │  │
│  │   • LiberarHabitacion(fecha, reserva_id)   │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  SQLite: habitaciones.db                         │
└──────────────────────────────────────────────────┘
```

**Decisiones clave:**

- **REST hacia afuera** → interoperabilidad, caché HTTP, depuración con `curl`.
- **gRPC hacia adentro** → tipado fuerte, mensajes compactos, contrato `.proto`.
- **Base de datos por servicio** → autonomía, sin accesos cruzados (T5).
- **Caché Redis** → reduce la latencia de las consultas de disponibilidad (O1).
- **Idempotencia** → un reintento no genera dos reservas (O2).

---

## Requisitos previos

- Docker Desktop 4.x o superior (incluye Docker Compose v2).
- Funciona en Windows, macOS y Linux.

---

## Cómo levantar el sistema

Desde la raíz del repositorio:

```bash
docker compose up --build
```

Espera a ver en los logs:

```
habitaciones  | [seed] 5 habitaciones insertadas
habitaciones  | [habitaciones] gRPC en :50051
reservas      | INFO:     Uvicorn running on http://0.0.0.0:8000
redis         | Ready to accept connections
```

Luego abre en el navegador:

- **Documentación interactiva (Swagger UI):** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health

---

## Endpoints principales

Todos los endpoints están versionados bajo `/v1`. La autenticación se realiza con
el header `X-API-Key: clave-demo-123`.

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| GET | `/health` | Healthcheck | No |
| POST | `/v1/huespedes` | Crear huésped | Sí |
| GET | `/v1/huespedes` | Listar huéspedes | Sí |
| GET | `/v1/huespedes/{id}` | Consultar huésped | Sí |
| GET | `/v1/disponibilidad/{fecha}` | Consultar disponibilidad (cacheada) | Sí |
| POST | `/v1/reservas` | Crear reserva (soporta `Idempotency-Key`) | Sí |
| GET | `/v1/reservas` | Listar reservas | Sí |
| GET | `/v1/reservas/{id}` | Consultar reserva | Sí |
| DELETE | `/v1/reservas/{id}` | Revertir reserva | Sí |

### Ejemplo de flujo completo

```bash
# 1. Crear un huésped
curl -X POST http://localhost:8000/v1/huespedes \
  -H "X-API-Key: clave-demo-123" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Ana Perez","email":"ana@example.com"}'

# 2. Consultar disponibilidad
curl http://localhost:8000/v1/disponibilidad/2026-01-15 \
  -H "X-API-Key: clave-demo-123"

# 3. Crear reserva (idempotente)
curl -X POST http://localhost:8000/v1/reservas \
  -H "X-API-Key: clave-demo-123" \
  -H "Idempotency-Key: demo-001" \
  -H "Content-Type: application/json" \
  -d '{"huesped_id":"PEGA-EL-ID","fecha":"2026-01-15"}'

# 4. Revertir reserva
curl -X DELETE http://localhost:8000/v1/reservas/PEGA-EL-ID \
  -H "X-API-Key: clave-demo-123"
```

### Idempotencia

El endpoint `POST /v1/reservas` acepta el header `Idempotency-Key`. Si se repite
con la misma key, devuelve la respuesta guardada sin crear una segunda reserva.
Esto protege contra reintentos por fallos de red: **el cliente nunca cobra ni
reserva dos veces**.

**Regla:** una `Idempotency-Key` distinta por reserva nueva. Si quieres simular
un reintento, repite la misma key a propósito.

---

## Modo de falla

Si el servicio de Habitaciones se cae, la API responde
**`503 Service Unavailable`** con header `Retry-After: 5`.

```bash
docker compose stop habitaciones
curl http://localhost:8000/v1/disponibilidad/2026-01-15 \
  -H "X-API-Key: clave-demo-123"
# -> 503 Service Unavailable, Retry-After: 5
docker compose start habitaciones
```

**Por qué 503 y no 500:** 500 significa bug del servidor; aquí el servidor
funciona bien, es una dependencia la que falla y el cliente puede reintentar.
Ver `docs/adr/ADR-004-resiliencia.md`.

---

## Estructura del repositorio

```
Manejo_microservicios_hotelarios/
├── docker-compose.yml
├── openapi.yaml
├── README.md
├── proto/
│   └── habitaciones.proto
├── docs/
│   ├── informe.tex
│   ├── informe.pdf
│   ├── adrs.tex
│   ├── referencias.bib
│   ├── adr/
│   │   ├── ADR-001-descomposicion.md
│   │   ├── ADR-002-rest-vs-grpc.md
│   │   ├── ADR-003-versionado.md
│   │   └── ADR-004-resiliencia.md
│   ├── experimento/
│   │   ├── medir_latencia.py
│   │   ├── comparar.py
│   │   ├── requirements.txt
│   │   ├── resultados_sin_cache.csv
│   │   ├── resultados_con_cache.csv
│   │   └── comparacion.csv
│   └── figuras/
│       ├── logo_udec.png
│       ├── arquitectura.png
│       └── grafico_latencia.png
├── servicio_habitaciones/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── server.py
│   ├── db.py
│   └── seed.py
└── servicio_reservas/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    ├── grpc_client.py
    ├── db.py
    ├── models.py
    ├── auth.py
    └── redis_cache.py
```

---

## Reproducir el experimento

El experimento mide el efecto de la caché Redis sobre la latencia del endpoint
`GET /v1/disponibilidad/{fecha}`. La hipótesis es que la caché reduce el p95 en
al menos 30%.

### Requisitos

```bash
pip install -r docs/experimento/requirements.txt
```

### Fase sin caché

1. Edita `docker-compose.yml` y pon `CACHE_ENABLED=false` en el servicio `reservas`.
2. Reinicia el servicio:

```bash
docker compose up -d reservas
```

3. Ejecuta:

```bash
cd docs/experimento
python medir_latencia.py sin
```

### Fase con caché

1. Edita `docker-compose.yml` y pon `CACHE_ENABLED=true`.
2. Reinicia el servicio:

```bash
docker compose up -d reservas
```

3. Precalienta la caché:

```bash
curl http://localhost:8000/v1/disponibilidad/2026-02-01 \
  -H "X-API-Key: clave-demo-123"
```

4. Ejecuta:

```bash
python medir_latencia.py con
python comparar.py
```

### Resultados

Los CSV crudos (`resultados_sin_cache.csv`, `resultados_con_cache.csv`) y la
tabla resumen (`comparacion.csv`) quedan versionados en `docs/experimento/`. El
gráfico se genera como `grafico_latencia.png`.

**Resultado obtenido:** la caché reduce el p95 de 8.80 ms a 4.98 ms, una mejora
del **43.4%** que supera la hipótesis planteada del 30%.

---

## Regenerar el contrato OpenAPI

FastAPI genera el contrato OpenAPI automáticamente. Para exportarlo al archivo
versionado:

```bash
curl http://localhost:8000/openapi.json -o openapi.yaml
```

---

## Bajar el sistema

```bash
# Detiene contenedores (mantiene datos)
docker compose down

# Detiene y borra volúmenes (borra datos)
docker compose down -v

# Detiene, borra volúmenes e imágenes locales (reconstruye todo)
docker compose down -v --rmi local
```

---

## Decisiones de arquitectura (ADRs)

Las cuatro decisiones solicitadas por el encargo están documentadas como
*Architecture Decision Records* en `docs/adr/`:

| ADR | Decisión |
|---|---|
| [ADR-001](docs/adr/ADR-001-descomposicion.md) | Descomposición en microservicios por bounded context |
| [ADR-002](docs/adr/ADR-002-rest-vs-grpc.md) | REST hacia afuera, gRPC hacia adentro |
| [ADR-003](docs/adr/ADR-003-versionado.md) | Contrato, versionado y evolución |
| [ADR-004](docs/adr/ADR-004-resiliencia.md) | Resiliencia y modos de falla |

Cada ADR sigue la plantilla del enunciado: Estado, Contexto, Alternativas
consideradas, Decisión, Justificación, Costo aceptado y Consecuencias.

---

## Declaración de uso de asistentes de IA

Este trabajo utilizó asistentes de IA (Claude, ChatGPT) como apoyo en:

- **Diseño inicial del contrato `.proto`** y revisión de compatibilidad de
  cambios en Protobuf.
- **Redacción inicial de los cuatro ADRs**, posteriormente revisados y ajustados
  por el autor para reflejar las decisiones efectivamente tomadas.
- **Estructura del proyecto** (separación de microservicios y responsabilidades
  de cada uno).
- **Depuración de configuración** de Docker, gRPC y matplotlib.

### Qué se verificó manualmente

- **Todo el código fue ejecutado y probado end-to-end** con
  `docker compose up --build` y pruebas en `/docs`.
- Los ADRs reflejan decisiones efectivamente tomadas y defendibles.
- El experimento de latencia fue ejecutado con 2000 peticiones × 3 repeticiones
  por fase, y sus datos son reales (ver `docs/experimento/`).
- Los códigos HTTP (200, 201, 404, 409, 503) fueron verificados manualmente en
  cada endpoint.
- El modo de falla (T7) fue probado apagando el contenedor de Habitaciones y
  verificando la respuesta `503` con `Retry-After`.

El autor comprende y puede explicar cada línea del código durante la defensa
oral.

---

## Video de la solución

Enlace al video de demostración:

- **Video:** (https://drive.google.com/file/d/1gBqX5uB18PvloHp5O847Zjgk_h6_yhn_/view?usp=sharing)

El video muestra:

1. El sistema completo levantándose con `docker compose up`.
2. Recorrido por los endpoints (crear huésped, crear reserva, ver rechazo por
   disponibilidad, revertir reserva).
3. Narración de las decisiones de diseño.

---

## Licencia

Trabajo académico. Universidad de Concepción — Facultad de Ingeniería, 2026.
