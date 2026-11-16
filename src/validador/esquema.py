"""Esquema único de datos. No depende del operador de planilla ni del método de lectura."""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel


class Estado(str, Enum):
    ESPERADO = "ESPERADO"
    RECIBIDO = "RECIBIDO"
    CUMPLE = "CUMPLE"
    PAGO_MAYOR = "PAGO MAYOR"
    PAGO_MENOR = "PAGO MENOR"
    SIN_PAGO = "SIN PAGO"
    MES_O_ARCHIVO_ERRADO = "MES O ARCHIVO ERRADO"
    REVISION_MANUAL = "REVISIÓN MANUAL"
    NO_ENTREGO = "NO ENTREGÓ"


HABILITAN = {Estado.CUMPLE, Estado.PAGO_MAYOR}
DEBEN_CORREGIR = {Estado.PAGO_MENOR, Estado.SIN_PAGO, Estado.MES_O_ARCHIVO_ERRADO}


class Soporte(BaseModel):
    """Lo que se extrae de un comprobante, venga de una plantilla, de Claude o de una persona."""

    es_soporte_pago: bool = True
    pagado: bool | None = None
    cedula: str | None = None
    nombre: str | None = None
    periodo: str | None = None  # "AAAA-MM"
    valor_pagado: int | None = None
    ibc_salud: int | None = None
    ibc_pension: int | None = None
    fecha_pago: date | None = None
    operador: str | None = None
    numero_planilla: str | None = None
    origen_lectura: str = "plantilla"  # plantilla | ia | manual


class Expectativa(BaseModel):
    """Una fila de la liquidación del mes: lo que se espera de un prestador."""

    cedula: str
    nombre: str
    valor_esperado: int
    devengado: int | None = None
    correo: str | None = None


class Reglas(BaseModel):
    tolerancia: int = 1000  # pesos; confirmado por la empresa
    dia_habil_corte: int = 5
    dia_clave: int = 15


class Resultado(BaseModel):
    estado: Estado
    motivo: str
    diferencia: int | None = None
    tardio: bool = False
    codigo_error: str | None = None

    @property
    def habilita(self) -> bool:
        return self.estado in HABILITAN
