# ADR-004 · Resiliencia y modos de falla

**Estado:** Aceptada

## Contexto

La API REST depende del servicio gRPC de Habitaciones. Si Habitaciones está
caído, lento, o devuelve errores, la API debe comportarse de forma predecible y
no arrastrar al cliente hacia timeouts indefinidos. Además, el operador necesita
saber si puede reintentar.

## Alternativas consideradas

- **Opción A — Sin timeout, sin caché.** El request espera indefinidamente.
  Inaceptable: si Habitaciones cuelga, toda la API cuelga.

- **Opción B — Timeout corto más caché Redis más 503 con `Retry-After`.** El
  cliente recibe una respuesta rápida y accionable; las consultas repetidas se
  sirven desde caché sin tocar Habitaciones.

- **Opción C — Devolver 200 con disponibilidad "desconocida" (fallback
  optimista).** Peligroso: podría confirmarse una reserva sin verificar
  disponibilidad real, que es exactamente el problema de overbooking que motivó
  este proyecto.

- **Opción D — Devolver 500.** Semánticamente incorrecto: 500 significa *bug*
  del servidor; aquí el servidor funciona bien, es una dependencia la que falla.

## Decisión

Timeout de 500 ms en el cliente gRPC. Si expira o falla, la API responde
`503 Service Unavailable` con header `Retry-After: 5`. La disponibilidad se
cachea en Redis con TTL de 30 s, y la caché se invalida al reservar o liberar.

## Justificación

- **503 y no 500:** la semántica HTTP distingue claramente. 500 es bug interno;
  503 es servicio temporalmente no disponible, reintentable. El header
  `Retry-After: 5` le dice al cliente cuándo reintentar.

- **No 200 optimista:** un sistema de reservas que miente sobre disponibilidad
  produce overbooking — el problema que estamos resolviendo.

- **Timeout de 500 ms:** en pruebas locales la consulta de disponibilidad
  promedia menos de 20 ms. 500 ms da 25× de margen y evita que un request
  cuelgue.

- **Caché de 30 s:** reduce la presión sobre Habitaciones en consultas repetidas
  y da una ventana de tolerancia breve si Habitaciones se reinicia. Costo: hasta
  30 s de desactualización en el peor caso, mitigado invalidando la caché al
  reservar o liberar.

## Costo aceptado

- Los clientes deben **manejar 503** con reintento. Está documentado en el
  OpenAPI.
- La caché introduce una **ventana de hasta 30 s** donde la disponibilidad
  mostrada puede no reflejar una reserva reciente hecha por otro camino (no por
  esta API). En nuestro caso, como toda reserva pasa por esta API, la
  invalidación elimina esa ventana en la práctica.
- 500 ms podría ser demasiado corto bajo carga extrema en el futuro. Es un
  parámetro configurable mediante la variable `GRPC_TIMEOUT_MS`.

## Consecuencias

La API degrada elegantemente en lugar de colgarse. El operador ve un `503` claro
y un `Retry-After` concreto. Si Habitaciones se cae por mucho tiempo, la caché
expira (30 s) y todas las consultas devuelven 503 hasta que se recupere. Es el
comportamiento correcto: es mejor rechazar que mentir.