from pydantic import BaseModel, EmailStr, Field


class HuespedCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    telefono: str | None = None


class HuespedOut(BaseModel):
    id: str
    nombre: str
    email: str
    telefono: str | None = None


class ReservaCreate(BaseModel):
    huesped_id: str
    fecha: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class ReservaOut(BaseModel):
    id: str
    huesped_id: str
    fecha: str
    estado: str
    habitacion_id: str | None = None
    creada_en: str