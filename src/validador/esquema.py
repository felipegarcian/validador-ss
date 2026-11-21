"""Esquema único de datos. No depende del operador de planilla ni del método de lectura.

Los nombres de estado son los del procedimiento de AZA (v3.0, sección 5) y se escriben
igual en la columna ESTADO de la Base para que los filtros funcionen.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from pydantic import BaseModel, Field


def al_peso(valor: float) -> int:
    """Redondeo al peso, mitad hacia arriba (no el redondeo bancario de Python)."""
    return int(Decimal(str(valor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class Estado(str, Enum):
    ESPERADO = "ESPERADO"                    # interno: aún no llega nada y no ha vencido el plazo
    OK = "OK"
    PAGO_DE_MAS = "PAGO DE MÁS"
    PENDIENTE_AJUSTE = "PENDIENTE AJUSTE"
    AJUSTADO = "AJUSTADO"
    OTRO_PERIODO = "OTRO PERIODO"
    PLANILLA_INCORRECTA = "PLANILLA INCORRECTA"
    NO_ENVIO = "NO ENVIÓ"
    SIN_HONORARIOS = "SIN HONORARIOS"
    REVISION_MANUAL = "REVISIÓN MANUAL"


HABILITAN = {Estado.OK, Estado.PAGO_DE_MAS, Estado.AJUSTADO}
DEBEN_CORREGIR = {Estado.PENDIENTE_AJUSTE, Estado.OTRO_PERIODO, Estado.PLANILLA_INCORRECTA, Estado.NO_ENVIO}
# Indicador de oportunidad (procedimiento, sección 8): solo estos estados pueden valer 1.
CUENTAN_UNO = {Estado.OK, Estado.PAGO_DE_MAS}


class Soporte(BaseModel):
    """Lo que se extrae de una planilla, venga de una plantilla, de Claude o de una persona."""

    es_planilla: bool = True
    pagado: bool | None = None
    cedula: str | None = None
    nombre: str | None = None
    periodo: str | None = None          # periodo de cotización "AAAA-MM"
    tipo_planilla: str | None = None    # I = independientes, E = empleador...
    tipo_empresa: str | None = None     # "INDEPENDIENTE"
    tipo_cotizante: str | None = None   # se espera "59"
    ibc_pension: int | None = None
    ibc_salud: int | None = None
    ibc_riesgos: int | None = None
    tarifa_arl: float | None = None     # en porcentaje: 1.044 = riesgo II
    intereses_mora: int | None = None
    valor_total: int | None = None
    fecha_pago: date | None = None
    operador: str | None = None
    numero_planilla: str | None = None
    origen_lectura: str = "plantilla"   # plantilla | ia | manual

    @property
    def ibc_pagado(self) -> int | None:
        """El menor entre IBC pensión, salud y riesgos (procedimiento 4.5). None si falta alguno."""
        valores = [self.ibc_pension, self.ibc_salud, self.ibc_riesgos]
        return None if any(v is None for v in valores) else min(valores)


class Expectativa(BaseModel):
    """Una fila de la Base para SS del mes."""

    cedula: str
    nombre: str
    base_rtte: int | None = None        # honorarios del mes; vacío o 0 = SIN HONORARIOS
    riesgo: str = "II"                  # I administrativo, II asesor
    especial: bool = False
    correo: str | None = None
    ibc_40_base: float | None = None    # lo que trae la Base en IBC 40%, solo para cruzar


class Reglas(BaseModel):
    porcentaje_ibc: float = 0.40
    smmlv: int = 1_750_905
    tolerancia_abajo: int = 1000        # hasta $1.000 por debajo = OK; cualquier peso por encima = PAGO DE MÁS
    tarifa_pension: float = 0.16
    tarifa_salud: float = 0.125
    tarifa_arl: dict[str, float] = Field(default_factory=lambda: {"I": 0.522, "II": 1.044})  # en %
    tipo_cotizante: str = "59"
    especial_a_revision: bool = True    # tabla de parámetros: "marcar siempre como revisión manual"
    dia_habil_corte: int = 5

    def ibc_requerido(self, exp: Expectativa) -> int | None:
        """BASE RTTE × 40 %, redondeado al peso. Especial: nunca menos que el SMMLV."""
        if not exp.base_rtte:
            return None
        ibc = al_peso(exp.base_rtte * self.porcentaje_ibc)
        return max(ibc, self.smmlv) if exp.especial else ibc


class Resultado(BaseModel):
    estado: Estado
    motivo: str
    ibc_requerido: int | None = None
    ibc_pagado: int | None = None
    diferencia: int | None = None       # IBC pagado − IBC requerido
    tardio: bool = False
    codigo_error: str | None = None
    observaciones: list[str] = Field(default_factory=list)
    aviso_riesgo: bool = False          # dispara la plantilla 7.5, no cambia el estado

    @property
    def habilita(self) -> bool:
        return self.estado in HABILITAN

    @property
    def indicador(self) -> int | None:
        """1 a tiempo y OK o PAGO DE MÁS; vacío sin honorarios; 0 en cualquier otro caso."""
        if self.estado == Estado.SIN_HONORARIOS:
            return None
        return 1 if (self.estado in CUENTAN_UNO and not self.tardio) else 0
