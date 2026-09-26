# ADR-001 · Descomposición en microservicios por bounded context

**Estado:** Aceptada

## Contexto

La Cadena Hotelera Costanera tiene dos sistemas que nacieron por separado y nunca
se integraron: **Habitaciones** gestiona la disponibilidad por fecha y su equipo
lo mantiene activamente; **Reservas** registra huéspedes y estadías, y necesita
consultar disponibilidad con altísima frecuencia. Sin integración, el overbooking
es frecuente. Hay que integrarlos sin reescribir ninguno de los dos.

## Alternativas consideradas

- **Opción A — Monolito único con una sola base de datos.** Simple de operar y
  sin latencia de red entre componentes. Pero obliga a reescribir ambos sistemas
  y acopla dos ciclos de vida que hoy son independientes.

- **Opción B — Dos microservicios con base de datos propia cada uno, comunicación
  interna vía gRPC.** Respeta la propiedad de cada sistema sobre su verdad,
  permite evolucionar cada uno por separado y alinea la frontera con un *bounded
  context* real.

- **Opción C — Dos servicios compartiendo una base de datos.** Menos código, pero
  rompe la autonomía: un cambio de esquema en Habitaciones rompe Reservas, y no
  se puede escalar solo el servicio que lo necesita.

## Decisión

Dos microservicios independientes, cada uno con su propio almacén, comunicados
por gRPC. La frontera está en el *bounded context*: **Habitaciones** es la verdad
sobre el inventario físico por fecha; **Reservas** es la verdad sobre huéspedes y
estadías contratadas.

## Justificación

La frontera respeta la realidad organizacional: Habitaciones y Reservas ya existen
y cada uno tiene su propio equipo. Un monolito forzaría a fusionar equipos y
ciclos de release. La duplicación de datos (Reservas guarda `habitacion_id` que
Habitaciones asignó) es intencional: cada servicio mantiene la información mínima
que necesita para operar sin consultar al otro en cada lectura.

## Costo aceptado

- **Consistencia eventual** entre los dos servicios: si Habitaciones cae justo
  después de que Reservas confirma, hay una ventana donde los datos podrían
  divergir. Se mitiga con la operación `LiberarHabitacion` en la reversión.
- **Mayor complejidad operativa**: tres contenedores más Redis en lugar de uno.
- **Latencia de red** entre servicios, mitigada parcialmente con caché Redis.

## Consecuencias

Cada servicio puede desplegarse, escalarse y versionarse por separado. Si mañana
Habitaciones agrega nuevos tipos de inventario (por ejemplo, salones de eventos),
Reservas no necesita cambiar mientras la interfaz gRPC se mantenga. Habría que
revisar esta decisión si el volumen de reservas bajara tanto que la operación
distribuida no se justificara.