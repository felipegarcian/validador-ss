"""Carga la liquidación del mes: una Expectativa por prestador, con la cédula como llave."""
from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from .esquema import Expectativa

# Nombres de columna por defecto. Se ajustan en config/reglas.yaml cuando llegue el Excel real.
COLUMNAS = {"cedula": "cedula", "nombre": "nombre", "devengado": "devengado",
            "valor_esperado": "valor_esperado"}


def limpiar_cedula(valor) -> str:
    return "".join(c for c in str(valor) if c.isdigit())


def cargar_liquidacion(ruta: str | Path, columnas: dict[str, str] | None = None) -> dict[str, Expectativa]:
    cols = {**COLUMNAS, **(columnas or {})}
    hoja = load_workbook(ruta, read_only=True, data_only=True).active
    filas = hoja.iter_rows(values_only=True)
    encabezado = [str(c).strip().lower() if c is not None else "" for c in next(filas)]
    pos = {}
    for campo, nombre in cols.items():
        if nombre.lower() in encabezado:
            pos[campo] = encabezado.index(nombre.lower())
    faltan = {"cedula", "nombre", "valor_esperado"} - pos.keys()
    if faltan:
        raise ValueError(f"La liquidación no trae las columnas: {sorted(faltan)}")

    resultado: dict[str, Expectativa] = {}
    for fila in filas:
        if fila[pos["cedula"]] in (None, ""):
            continue
        cedula = limpiar_cedula(fila[pos["cedula"]])
        resultado[cedula] = Expectativa(
            cedula=cedula,
            nombre=str(fila[pos["nombre"]]).strip(),
            valor_esperado=int(round(float(fila[pos["valor_esperado"]]))),
            devengado=int(round(float(fila[pos["devengado"]]))) if "devengado" in pos and fila[pos["devengado"]] is not None else None,
        )
    return resultado
