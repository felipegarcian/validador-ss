"""Escribe en los archivos que AZA ya usa, con su mismo formato.

- Base para SS: llena IBC PAGADO, NUEVO PENSION, NUEVO SALUD y ESTADO (procedimiento 3.1 y 5).
  Siempre sobre una COPIA; el original no se toca.
- Formato Ajuste Seguridad Social: un bloque por prestador en PENDIENTE AJUSTE (sección 6), con
  fórmulas completas y el texto del riesgo correcto (el formato actual trae fijo "riesgo II (1.044)"
  y un bloque sin la fila de pensión).
"""
from __future__ import annotations

import shutil
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from ..conciliacion import Mes
from ..esquema import Estado
from ..expectativas import limpiar_cedula, ubicar_columnas
from ..salidas.correos import MESES

LLENA_IBC = {Estado.PAGO_DE_MAS, Estado.PENDIENTE_AJUSTE, Estado.AJUSTADO}


def escribir_base(original: str | Path, mes: Mes, destino: str | Path) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(original, destino)
    libro = load_workbook(destino)
    hoja = libro.worksheets[0]
    fila_enc, pos = ubicar_columnas(hoja)
    if "estado" not in pos:
        pos["estado"] = hoja.max_column
        hoja.cell(fila_enc, pos["estado"] + 1, "ESTADO")
    r = mes.reglas
    for fila in hoja.iter_rows(min_row=fila_enc + 1):
        cedula = limpiar_cedula(fila[pos["cedula"]].value) if fila[pos["cedula"]].value else None
        res = mes.estados.get(cedula or "")
        if res is None:
            continue
        def poner(campo, valor):
            if campo in pos:
                hoja.cell(fila[0].row, pos[campo] + 1, valor)
        poner("estado", res.estado.value)
        if res.estado in LLENA_IBC and res.ibc_pagado is not None:
            poner("ibc_pagado", res.ibc_pagado)
            poner("nuevo_pension", round(res.ibc_pagado * r.tarifa_pension))
            poner("nuevo_salud", round(res.ibc_pagado * r.tarifa_salud))
        elif res.estado == Estado.OK:
            poner("nuevo_pension", 0)
            poner("nuevo_salud", 0)
    libro.save(destino)
    return destino


def escribir_formato_ajuste(mes: Mes, destino: str | Path) -> Path | None:
    pendientes = [(c, r) for c, r in mes.estados.items() if r.estado == Estado.PENDIENTE_AJUSTE]
    if not pendientes:
        return None
    libro = Workbook()
    hoja = libro.active
    anio, m = mes.periodo.split("-")
    nombre_mes = MESES[int(m) - 1]
    hoja.title = f"{nombre_mes.title()} {anio}"
    negrita = Font(bold=True)
    fila = 1
    for cedula, res in pendientes:
        exp = mes.expectativas[cedula]
        tarifa_arl = mes.reglas.tarifa_arl[exp.riesgo]
        base_ibc = "SMMLV (Especial)" if exp.especial else "40 % de los honorarios del mes"
        hoja.cell(fila, 1, "SEGURIDAD SOCIAL - PRESTACIÓN DE SERVICIOS").font = negrita
        hoja.cell(fila + 1, 1, "NOMBRE Y APELLIDO"); hoja.cell(fila + 1, 2, exp.nombre)
        hoja.cell(fila + 2, 1, f"El IBC es el {base_ibc} y la ARL es por riesgo {exp.riesgo} "
                               f"({str(tarifa_arl).replace('.', ',')} %)")
        hoja.cell(fila + 2, 2, f"IBC {nombre_mes.upper()}"); hoja.cell(fila + 2, 3, "VALOR PAGADO")
        hoja.cell(fila + 2, 4, "AJUSTE")
        hoja.cell(fila + 3, 1, "IBC MES"); hoja.cell(fila + 3, 2, exp.base_rtte)
        f = fila + 4
        hoja.cell(f, 1, "IBC requerido"); hoja.cell(f, 2, res.ibc_requerido); hoja.cell(f, 3, res.ibc_pagado)
        hoja.cell(f, 4, f"=B{f}-C{f}")
        for i, (concepto, tarifa) in enumerate([("Pensión", mes.reglas.tarifa_pension),
                                                 ("Salud", mes.reglas.tarifa_salud),
                                                 ("ARL", tarifa_arl / 100)], start=1):
            hoja.cell(f + i, 1, concepto)
            for col in "BC":
                hoja[f"{col}{f + i}"] = f"=ROUND({col}{f}*{tarifa},0)"
            hoja[f"D{f + i}"] = f"=B{f + i}-C{f + i}"
        t = f + 5
        hoja.cell(t, 1, "Total a pagar").font = negrita
        for col in "BCD":
            hoja[f"{col}{t}"] = f"=SUM({col}{f + 1}:{col}{f + 3})"
        hoja.cell(t, 5, "ajuste")
        fila = t + 2
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(destino)
    return destino
