"""Control del mes (Anexo A.2 del procedimiento): una fila por prestador, más Bitácora,
Correos (borradores para aprobar) y Contabilidad. Se regenera completo desde el estado.

En Office 365 la escritura pasa por la API de Excel de Microsoft Graph o por la ruta P:\\.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from ..conciliacion import Mes
from . import correos

COLUMNAS = ["Cédula", "Nombre", "Riesgo", "Especial", "Base RTTE", "IBC requerido", "Periodo", "Fecha de pago",
            "Fecha del correo", "Tipo cotizante", "IBC pensión", "IBC salud", "IBC riesgos", "Tarifa ARL",
            "IBC pagado", "Diferencia", "Estado", "Indicador", "Habilita pago", "Motivo", "Observaciones",
            "Operador", "Planilla No."]


def escribir(mes: Mes, ruta: str | Path) -> Path:
    libro = Workbook()
    control = libro.active
    control.title = "Control"
    control.append(COLUMNAS)
    for cedula, exp in mes.expectativas.items():
        r = mes.estados[cedula]
        s = (mes.soportes.get(cedula) or [None])[-1]
        control.append([
            cedula, exp.nombre, exp.riesgo, "Especial" if exp.especial else "", exp.base_rtte, r.ibc_requerido,
            s.periodo if s else None, s.fecha_pago if s else None, mes.recibidos.get(cedula),
            s.tipo_cotizante if s else None, s.ibc_pension if s else None, s.ibc_salud if s else None,
            s.ibc_riesgos if s else None, s.tarifa_arl if s else None, r.ibc_pagado, r.diferencia,
            r.estado.value, r.indicador, "sí" if r.habilita else "no", r.motivo, " ".join(r.observaciones),
            s.operador if s else None, s.numero_planilla if s else None,
        ])
    # Procedimiento: toda planilla recibida cruza con una cédula o va a REVISIÓN MANUAL. Las que no
    # cruzan se agregan al final para que la analista las vea y decida.
    for caso in mes.sin_identificar:
        r = caso["resultado"]
        fila = {"Cédula": "", "Nombre": f"SIN IDENTIFICAR: {caso['remitente'] or caso['correo'] or '?'}",
                "Fecha del correo": caso["fecha"], "Estado": r.estado.value, "Indicador": None,
                "Habilita pago": "no", "Motivo": f"{r.codigo_error} {r.motivo}",
                "Observaciones": f"Archivo: {caso['archivo']}. Correo: {caso['correo'] or 'desconocido'}."}
        control.append([fila.get(c) for c in COLUMNAS])

    bitacora = libro.create_sheet("Bitácora")
    bitacora.append(["Fecha", "Cédula", "Evento", "Detalle"])
    for linea in mes.bitacora:
        bitacora.append([linea["fecha"], linea["cedula"], linea["evento"], linea["detalle"]])

    hoja_correos = libro.create_sheet("Correos")
    hoja_correos.append(["Cédula", "Para", "Causal", "Asunto", "Cuerpo", "Aprobado por", "Enviado"])
    for b in correos.borradores(mes):
        hoja_correos.append([b["cedula"], b["para"], b["causal"], b["asunto"], b["cuerpo"], "", ""])

    conta = libro.create_sheet("Contabilidad")
    conta.append(["Cédula", "Nombre", "Estado", "Autoriza pago de honorarios"])
    for cedula, exp in mes.expectativas.items():
        r = mes.estados[cedula]
        conta.append([cedula, exp.nombre, r.estado.value, "sí" if r.habilita else "no"])

    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    libro.save(ruta)
    return ruta
