FROM python:3.11-slim

WORKDIR /app

COPY servicio_habitaciones/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto/ /app/proto/
RUN mkdir -p /app/generated && \
    python -m grpc_tools.protoc \
      -I/app/proto \
      --python_out=/app/generated \
      --grpc_python_out=/app/generated \
      /app/proto/habitaciones.proto && \
    touch /app/generated/__init__.py

COPY servicio_habitaciones/server.py servicio_habitaciones/db.py servicio_habitaciones/seed.py ./

ENV PYTHONUNBUFFERED=1
EXPOSE 50051
CMD ["python", "server.py"]