"""Carril 1: lectura por plantillas de formatos conocidos.

Cada plantilla reconoce el texto de un operador y devuelve un Soporte.
La plantilla DEMO lee el formato ficticio de datos_prueba; las reales se agregan
cuando lleguen comprobantes de cada operador (ver plantillas_operador/README.md).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Callable

from ..esquema import Soporte


@dataclass
class Plantilla:
    operador: str
    reconoce: Callable[[str], bool]
    extraer: Callable[[str], Soporte]


def _numero(texto: str) -> int:
    return int(re.sub(r"\D", "", texto))


def _campo(patron: str, texto: str) -> str | None:
    m = re.search(patron, texto, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _extraer_demo(texto: str) -> Soporte:
    valor = _campo(r"Total pagado:\s*\$?\s*([\d.,]+)", texto)
    fecha = _campo(r"Fecha de pago:\s*(\d{4}-\d{2}-\d{2})", texto)
    estado = (_campo(r"Estado:\s*(\w+)", texto) or "").upper()
    return Soporte(
        operador="OPERADOR DEMO",
        cedula=re.sub(r"\D", "", _campo(r"Identificaci[oó]n:\s*([\d.]+)", texto) or "") or None,
        nombre=_campo(r"Cotizante:\s*(.+)", texto),
        periodo=_campo(r"Per[ií]odo:\s*(\d{4}-\d{2})", texto),
        valor_pagado=_numero(valor) if valor else None,
        fecha_pago=date.fromisoformat(fecha) if fecha else None,
        numero_planilla=_campo(r"Planilla No\.?\s*(\d+)", texto),
        pagado=estado == "PAGADA" if estado else None,
    )


REGISTRO: list[Plantilla] = [
    Plantilla("OPERADOR DEMO", lambda t: "OPERADOR DEMO" in t.upper(), _extraer_demo),
]


def leer(texto: str) -> Soporte | None:
    """Devuelve el Soporte si alguna plantilla reconoce el texto; None si hay que ir al carril 2."""
    for plantilla in REGISTRO:
        if plantilla.reconoce(texto):
            return plantilla.extraer(texto)
    return None
