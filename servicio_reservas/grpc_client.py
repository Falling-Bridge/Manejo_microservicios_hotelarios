import os, sys
import grpc

sys.path.insert(0, "/app/generated")
import habitaciones_pb2 as pb
import habitaciones_pb2_grpc as pb_grpc

GRPC_TARGET = os.getenv("HABITACIONES_GRPC", "habitaciones:50051")
TIMEOUT_MS = int(os.getenv("GRPC_TIMEOUT_MS", "500"))


class HabitacionesUnavailable(Exception):
    """La dependencia gRPC no respondió a tiempo o está caída."""


def _stub():
    return pb_grpc.HabitacionesServiceStub(grpc.insecure_channel(GRPC_TARGET))


def consultar_disponibilidad(fecha):
    try:
        r = _stub().ConsultarDisponibilidad(
            pb.ConsultaRequest(fecha=fecha), timeout=TIMEOUT_MS / 1000.0)
        return {"fecha": r.fecha, "habitaciones_libres": r.habitaciones_libres,
                "ids_habitaciones": list(r.ids_habitaciones)}
    except grpc.RpcError as e:
        raise HabitacionesUnavailable(str(e))


def reservar_habitacion(fecha, reserva_id):
    try:
        r = _stub().ReservarHabitacion(
            pb.ReservaHabitacionRequest(fecha=fecha, reserva_id=reserva_id),
            timeout=TIMEOUT_MS / 1000.0)
        return {"ok": r.ok, "mensaje": r.mensaje, "habitacion_id": r.habitacion_id}
    except grpc.RpcError as e:
        raise HabitacionesUnavailable(str(e))


def liberar_habitacion(fecha, reserva_id):
    try:
        r = _stub().LiberarHabitacion(
            pb.LiberarHabitacionRequest(fecha=fecha, reserva_id=reserva_id),
            timeout=TIMEOUT_MS / 1000.0)
        return {"ok": r.ok, "mensaje": r.mensaje, "habitacion_id": r.habitacion_id}
    except grpc.RpcError as e:
        raise HabitacionesUnavailable(str(e))