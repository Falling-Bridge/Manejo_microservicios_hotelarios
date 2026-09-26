# ADR-002 · REST hacia afuera, gRPC hacia adentro

**Estado:** Aceptada

## Contexto

El sistema tiene dos caras: una **pública** (personal de la organización y un
futuro portal web consumirán huéspedes y reservas) y una **interna** (Reservas
consulta disponibilidad a Habitaciones con altísima frecuencia). Los requisitos
de cada cara son distintos: la pública necesita interoperabilidad y facilidad de
depuración; la interna necesita eficiencia, tipado fuerte y contrato formal.

## Alternativas consideradas

- **Opción A — REST/JSON en ambas caras.** Uniforme, fácil de depurar con `curl`,
  interoperable con cualquier cliente. Pero el JSON es verboso, la validación es
  débil (todo es *string* hasta que el servidor lo parsea) y en la cara interna
  el volumen alto penaliza el tamaño del payload.

- **Opción B — gRPC en ambas caras.** Binario compacto, tipado fuerte, contratos
  formales en `.proto`. Pero un cliente externo (navegador, `curl`, Postman) no
  puede consumirlo sin generar *stubs*, y no aprovecha la caché HTTP estándar.

- **Opción C — REST en la cara pública, gRPC en la interna.** Cada protocolo
  donde sus ventajas importan: REST por interoperabilidad y depuración; gRPC por
  rendimiento, tipado y contrato binario.

## Decisión

REST/JSON en la API pública (puerto 8000, servicio Reservas), gRPC/Protobuf en la
comunicación interna (puerto 50051, servicio Habitaciones).

## Justificación

- **REST afuera:** el consumidor es un navegador o un cliente HTTP genérico.
  `curl` y Swagger (`/docs`) permiten probar sin generar código. La caché HTTP y
  los headers estándar (incluido `Idempotency-Key`) son directos de implementar.
  El versionado por URL (`/v1/`) es visible y explícito.

- **gRPC adentro:** el mensaje `DisponibilidadResponse` en Protobuf pesa
  aproximadamente la mitad que su equivalente JSON. El tipado fuerte evita
  errores de parseo entre servicios y el contrato `.proto` versionado actúa como
  fuente única de verdad para ambos lados.

## Costo aceptado

- **Dos lenguajes de descripción** (OpenAPI y Protobuf) y dos generadores de
  código en el build.
- **Depurar gRPC es más incómodo** que un `curl`: requiere `grpcurl` o un cliente
  propio.
- El equipo debe conocer **ambas herramientas**.

## Consecuencias

Agregar un consumidor externo no requiere tocar gRPC. Cambiar la firma interna no
requiere tocar la API pública si el adaptador se mantiene. Si mañana aparece un
cliente móvil nativo, se puede exponer gRPC directamente sin rehacer la lógica.