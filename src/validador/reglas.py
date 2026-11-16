"""Reglas de validación. Código determinista: misma entrada, mismo resultado.

Regla central (confirmada por la empresa): se compara lo pagado en el comprobante
con lo esperado en el Excel del mes, con tolerancia por redondeo.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .esquema import Estado, Expectativa, Reglas, Resultado, Soporte


def cargar_reglas(ruta: str | Path) -> Reglas:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8")) or {}
    return Reglas(**(datos.get("reglas") or {}))


def evaluar(
    soporte: Soporte,
    esperado: Expectativa | None,
    periodo: str,
    reglas: Reglas,
    recibido: date | None = None,
    fecha_limite: date | None = None,
) -> Resultado:
    """Devuelve el estado de un soporte frente a la fila esperada del prestador."""
    tardio = bool(recibido and fecha_limite and recibido > fecha_limite)

    if not soporte.es_soporte_pago:
        return Resultado(estado=Estado.MES_O_ARCHIVO_ERRADO, tardio=tardio,
                         motivo="El archivo no es un comprobante de seguridad social.")
    if esperado is None:
        return Resultado(estado=Estado.REVISION_MANUAL, tardio=tardio, codigo_error="I-01",
                         motivo="La cédula no está en la liquidación del mes.")
    if soporte.periodo is None or soporte.valor_pagado is None:
        return Resultado(estado=Estado.REVISION_MANUAL, tardio=tardio, codigo_error="L-03",
                         motivo="Faltan campos obligatorios en la lectura.")
    if soporte.periodo != periodo:
        return Resultado(estado=Estado.MES_O_ARCHIVO_ERRADO, tardio=tardio,
                         motivo=f"El soporte es de {soporte.periodo} y se esperaba {periodo}.")
    if soporte.pagado is False:
        return Resultado(estado=Estado.SIN_PAGO, tardio=tardio,
                         motivo="La planilla no muestra el pago realizado.")

    diferencia = soporte.valor_pagado - esperado.valor_esperado
    if diferencia < -reglas.tolerancia:
        return Resultado(estado=Estado.PAGO_MENOR, diferencia=diferencia, tardio=tardio,
                         motivo=f"Pagó {abs(diferencia)} pesos menos de lo esperado.")
    if diferencia > reglas.tolerancia:
        return Resultado(estado=Estado.PAGO_MAYOR, diferencia=diferencia, tardio=tardio,
                         motivo="Pagó más de lo esperado; se conserva porque impacta la retención.")
    return Resultado(estado=Estado.CUMPLE, diferencia=diferencia, tardio=tardio,
                     motivo="Lo pagado coincide con lo esperado.")
