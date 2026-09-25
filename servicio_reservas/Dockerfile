FROM python:3.11-slim

WORKDIR /app

COPY servicio_reservas/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/ /app/proto/
RUN mkdir -p /app/generated && \
    python -m grpc_tools.protoc \
      -I/app/proto \
      --python_out=/app/generated \
      --grpc_python_out=/app/generated \
      /app/proto/habitaciones.proto && \
    touch /app/generated/__init__.py

COPY servicio_reservas/main.py \
     servicio_reservas/db.py \
     servicio_reservas/models.py \
     servicio_reservas/auth.py \
     servicio_reservas/grpc_client.py \
     servicio_reservas/redis_cache.py ./

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]