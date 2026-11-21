"""Carga la Base para SS del mes: una Expectativa por prestador, con la cédula como llave.

Formato real (Base de octubre 2026): fila 1 con los dos bloques, fila 2 con encabezados,
datos desde la fila 3. Las columnas se ubican por nombre de encabezado, no por letra
(procedimiento 3.1). Algunos encabezados traen el mes ("BASE RTTE OCTUBRE 2026") o el
riesgo ("ARL RIESGO II"), por eso se buscan por prefijo.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

from openpyxl import load_workbook

from .esquema import Expectativa

# campo -> prefijos aceptados (ya normalizados). Editables en config/reglas.yaml.
COLUMNAS: dict[str, list[str]] = {
    "nombre": ["asesor", "nombre"],
    "cedula": ["cedula"],
    "correo": ["correo"],
    "riesgo": ["tipo de riesgo"],
    "especial": ["especial"],
    "base_rtte": ["base rtte"],
    "ibc_40": ["ibc 40"],
    "ibc_pagado": ["ibc pagado"],
    "nuevo_pension": ["nuevo pension"],
    "nuevo_salud": ["nuevo salud"],
    "estado": ["estado", "observaciones"],
}
OBLIGATORIAS = {"nombre", "cedula", "base_rtte"}


def normalizar(texto) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def limpiar_cedula(valor) -> str:
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return "".join(c for c in str(valor) if c.isdigit())


def ubicar_columnas(hoja, columnas: dict[str, list[str]] | None = None, max_filas: int = 10):
    """Devuelve (fila_encabezado, {campo: índice de columna 0-based})."""
    cols = {**COLUMNAS, **(columnas or {})}
    for fila in hoja.iter_rows(min_row=1, max_row=max_filas):
        nombres = [normalizar(c.value) for c in fila]
        if not any(n.startswith("cedula") for n in nombres):
            continue
        pos: dict[str, int] = {}
        for campo, prefijos in cols.items():
            for i, n in enumerate(nombres):
                if n and any(n.startswith(p) for p in prefijos):
                    pos[campo] = i
                    break
        faltan = OBLIGATORIAS - pos.keys()
        if faltan:
            raise ValueError(f"La Base no trae las columnas: {sorted(faltan)}")
        return fila[0].row, pos
    raise ValueError("No se encontró la fila de encabezados (ninguna celda dice CÉDULA).")


def cargar_base(ruta: str | Path, columnas: dict[str, list[str]] | None = None) -> dict[str, Expectativa]:
    hoja = load_workbook(ruta, data_only=True).worksheets[0]
    fila_enc, pos = ubicar_columnas(hoja, columnas)

    def valor(fila, campo):
        return fila[pos[campo]] if campo in pos else None

    resultado: dict[str, Expectativa] = {}
    for fila in hoja.iter_rows(min_row=fila_enc + 1, values_only=True):
        if valor(fila, "cedula") in (None, ""):
            continue
        cedula = limpiar_cedula(valor(fila, "cedula"))
        base = valor(fila, "base_rtte")
        ibc40 = valor(fila, "ibc_40")
        resultado[cedula] = Expectativa(
            cedula=cedula,
            nombre=" ".join(str(valor(fila, "nombre") or "").split()),
            base_rtte=int(round(float(base))) if base not in (None, "") else None,
            riesgo=str(valor(fila, "riesgo") or "II").strip().upper(),
            especial=normalizar(valor(fila, "especial")) == "especial",
            correo=(str(valor(fila, "correo")).strip() or None) if valor(fila, "correo") else None,
            ibc_40_base=float(ibc40) if isinstance(ibc40, (int, float)) else None,
        )
    return resultado


# Compatibilidad con la versión anterior
cargar_liquidacion = cargar_base
