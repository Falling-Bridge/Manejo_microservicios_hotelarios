# ADR-003 · Contrato, versionado y evolución

**Estado:** Aceptada

## Contexto

Ambos contratos (OpenAPI de la API pública y `.proto` del servicio interno) van a
evolucionar. Hay que decidir cómo, sin romper a los consumidores actuales.

## Alternativas consideradas

- **Opción A — Sin versionado explícito.** Menos ruido en las URLs. Pero
  cualquier cambio rompe a todos los consumidores simultáneamente.

- **Opción B — Versionado por URL (`/v1/`, `/v2/`).** Explícito, cacheable, fácil
  de rutear y de documentar. Costo: duplicar endpoints mientras conviven
  versiones.

- **Opción C — Versionado por header** (`Accept: application/vnd.api.v1+json`).
  URLs limpias, pero más difícil de probar en el navegador y menos común.

## Decisión

Versionado por URL para REST (`/v1/`). Versionado por **compatibilidad de campos**
en Protobuf: nunca reutilizar tags, solo agregar campos opcionales; los cambios
incompatibles van a un nuevo paquete `habitaciones.v2`.

## Justificación

En REST, `/v1/` es visible, cacheable y trivial de probar en el navegador. En
Protobuf, el sistema de tags numéricos ya está diseñado para evolucionar sin
romper. La regla concreta aplicada en este proyecto:

| Cambio | ¿Compatible? |
|---|---|
| Agregar campo opcional con tag nuevo | Sí |
| Agregar valor a un enum al final | Sí |
| Renombrar un campo (mismo tag) | Sí (el tag es la identidad) |
| Cambiar tipo de un campo existente | No |
| Eliminar un campo | No |

## Costo aceptado

- **Duplicación de endpoints** mientras coexistan `/v1/` y `/v2/`.
- Debe existir **disciplina de equipo**: nunca reutilizar tags en `.proto`.
- Hay que mantener **dos versiones de la documentación**.

## Consecuencias

Los consumidores actuales seguirán funcionando aunque se agreguen campos. Los
cambios incompatibles requieren desplegar `/v2/` en paralelo y anunciar la
deprecación de `/v1/` con al menos una versión de antelación. Los consumidores se
enteran por: (a) changelog en el repositorio, (b) header `Deprecation` en la
respuesta, (c) tests de contrato (O4) que fallan en integración continua antes
del despliegue.