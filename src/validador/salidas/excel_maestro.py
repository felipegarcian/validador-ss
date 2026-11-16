"""Excel maestro del mes: Control, Bitácora y Contabilidad. Se regenera completo desde el estado.

En el MVP se escribe con openpyxl sobre un archivo local. En Office 365 la escritura
pasa por la API de Excel de Microsoft Graph (pendiente: probar con el archivo abierto).
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from ..conciliacion import Mes


def escribir(mes: Mes, ruta: str | Path, pagados: dict[str, int] | None = None) -> Path:
    pagados = pagados or {}
    libro = Workbook()

    control = libro.active
    control.title = "Control"
    control.append(["Cédula", "Nombre", "Valor esperado", "Valor pagado", "Diferencia", "Estado", "Tardío", "Motivo"])
    for cedula, exp in mes.expectativas.items():
        r = mes.estados[cedula]
        control.append([cedula, exp.nombre, exp.valor_esperado, pagados.get(cedula), r.diferencia,
                        r.estado.value, "sí" if r.tardio else "", r.motivo])

    bitacora = libro.create_sheet("Bitácora")
    bitacora.append(["Fecha", "Cédula", "Evento", "Detalle"])
    for linea in mes.bitacora:
        bitacora.append([linea["fecha"], linea["cedula"], linea["evento"], linea["detalle"]])

    conta = libro.create_sheet("Contabilidad")
    conta.append(["Cédula", "Nombre", "Valor esperado", "Valor pagado", "Estado"])
    for cedula, exp in mes.expectativas.items():
        r = mes.estados[cedula]
        if r.habilita:
            conta.append([cedula, exp.nombre, exp.valor_esperado, pagados.get(cedula), r.estado.value])

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta)
    return ruta
