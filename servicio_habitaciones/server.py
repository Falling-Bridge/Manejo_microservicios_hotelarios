import os, sys, time
from concurrent import futures
import grpc

sys.path.insert(0, "/app/generated")
import habitaciones_pb2 as pb
import habitaciones_pb2_grpc as pb_grpc

from db import (init_db, habitaciones_libres, reservar_habitacion,
                liberar_habitacion, disponibilidad_rango)
from seed import seed


class Servicer(pb_grpc.HabitacionesServiceServicer):

    def ConsultarDisponibilidad(self, request, context):
        libres = habitaciones_libres(request.fecha)
        return pb.DisponibilidadResponse(
            fecha=request.fecha,
            habitaciones_libres=len(libres),
            ids_habitaciones=libres,
        )

    def ListarDisponibilidad(self, request, context):
        dias = disponibilidad_rango(request.fecha_inicio, request.fecha_fin)
        return pb.ListaDisponibilidadResponse(
            dias=[pb.DisponibilidadDia(fecha=f, habitaciones_libres=n) for f, n in dias]
        )

    def ReservarHabitacion(self, request, context):
        hab = reservar_habitacion(request.fecha, request.reserva_id)
        if hab is None:
            return pb.OperacionResponse(ok=False, mensaje="Sin disponibilidad", habitacion_id="")
        return pb.OperacionResponse(ok=True, mensaje="Reservada", habitacion_id=hab)

    def LiberarHabitacion(self, request, context):
        hab = liberar_habitacion(request.fecha, request.reserva_id)
        if hab is None:
            return pb.OperacionResponse(ok=False, mensaje="No había ocupación", habitacion_id="")
        return pb.OperacionResponse(ok=True, mensaje="Liberada", habitacion_id=hab)


def serve():
    seed()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb_grpc.add_HabitacionesServiceServicer_to_server(Servicer(), server)
    port = os.getenv("GRPC_PORT", "50051")
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"[habitaciones] gRPC en :{port}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()