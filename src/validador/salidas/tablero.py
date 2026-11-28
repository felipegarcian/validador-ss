"""Contrato de datos del tablero: tablero_AAAA-MM.json (docs/TABLERO.md, Fase 1).

El tablero solo muestra lo que trae este archivo; no calcula estados ni cifras. Todo sale del
estado del mes (`conciliacion.Mes`) y de los borradores de `correos.py`, igual que el Excel
maestro. Los campos `explicacion` y `resumen` quedan vacíos hasta que exista la capa de IA
(Fase 3); entonces se llenan con su origen.

Los identificadores son estables dentro del mes: c-NN para cada fila de la Base, s-NN para los
soportes sin identificar y m-NN para los correos, en el orden en que los produce el motor.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from .. import calendario
from ..conciliacion import Mes
from ..esquema import Estado
from . import correos, verificador

VERSION = 1


def _indicadores(mes: Mes, hoy: date) -> dict:
    resultados = list(mes.estados.values())
    con_indicador = [r.indicador for r in resultados if r.indicador is not None]
    con_honorarios = [r for r in resultados if r.estado != Estado.SIN_HONORARIOS]
    habilitados = sum(r.habilita for r in con_honorarios)
    por_estado: dict[str, int] = {}
    por_codigo: dict[str, int] = {}
    for r in resultados + [c["resultado"] for c in mes.sin_identificar]:
        por_estado[r.estado.value] = por_estado.get(r.estado.value, 0) + 1
        if r.codigo_error:
            por_codigo[r.codigo_error] = por_codigo.get(r.codigo_error, 0) + 1
    por_origen: dict[str, int] = {}
    for lista in mes.soportes.values():
        if lista:
            origen = lista[-1].origen_lectura
            por_origen[origen] = por_origen.get(origen, 0) + 1
    return {
        "oportunidad": {"cumplen": sum(con_indicador), "total": len(con_indicador),
                        "valor": round(sum(con_indicador) / len(con_indicador), 4) if con_indicador else None},
        "habilitados": {"cumplen": habilitados, "total": len(con_honorarios),
                        "valor": round(habilitados / len(con_honorarios), 4) if con_honorarios else None},
        "por_estado": dict(sorted(por_estado.items())),
        "por_codigo": dict(sorted(por_codigo.items())),
        "por_origen": dict(sorted(por_origen.items())),
        "sin_identificar": len(mes.sin_identificar),
        "dias_habiles_al_corte": calendario.dias_habiles_hasta(hoy, mes.fecha_limite),
    }


def _caso(id_: str, resultado, **extra) -> dict:
    caso = {"id": id_, "estado": resultado.estado.value, "motivo": resultado.motivo,
            "codigo_error": resultado.codigo_error, "ibc_requerido": resultado.ibc_requerido,
            "ibc_pagado": resultado.ibc_pagado, "diferencia": resultado.diferencia, "tardio": resultado.tardio,
            "indicador": resultado.indicador, "habilita": resultado.habilita,
            "aviso_riesgo": resultado.aviso_riesgo, "observaciones": list(resultado.observaciones),
            "explicacion": None, "explicacion_origen": None}
    caso.update(extra)
    return caso


def construir(mes: Mes, generado: datetime | None = None, hoy: date | None = None) -> dict:
    """El contenido completo del tablero para el mes. `generado` y `hoy` se fijan en las pruebas."""
    generado = generado or datetime.now().replace(microsecond=0)
    hoy = hoy or generado.date()

    casos, id_por_cedula = [], {}
    for i, (cedula, exp) in enumerate(mes.expectativas.items(), start=1):
        r = mes.estados[cedula]
        s = (mes.soportes.get(cedula) or [None])[-1]
        id_por_cedula[cedula] = f"c-{i:02d}"
        recibido = mes.recibidos.get(cedula)
        casos.append(_caso(
            f"c-{i:02d}", r, cedula=cedula, nombre=exp.nombre, correo=exp.correo or mes.remitentes.get(cedula),
            riesgo=exp.riesgo, especial=exp.especial, base_rtte=exp.base_rtte,
            fecha_recibido=recibido.isoformat() if recibido else None,
            periodo_soporte=s.periodo if s else None, operador=s.operador if s else None,
            numero_planilla=s.numero_planilla if s else None, origen_lectura=s.origen_lectura if s else None))

    # Sin identificar: no tienen fila en la Base. Los que llevan correo se enlazan en orden.
    ids_sin_identificar_con_correo = []
    for j, caso in enumerate(mes.sin_identificar, start=1):
        r = caso["resultado"]
        casos.append(_caso(
            f"s-{j:02d}", r, cedula=None, nombre=f"SIN IDENTIFICAR: {caso['remitente'] or caso['correo'] or '?'}",
            correo=caso["correo"] or None, riesgo=None, especial=False, base_rtte=None,
            fecha_recibido=caso["fecha"], periodo_soporte=None, operador=None, numero_planilla=None,
            origen_lectura=None, archivo=caso["archivo"]))
        if correos.causal_de(r):
            ids_sin_identificar_con_correo.append(f"s-{j:02d}")

    lista_correos = []
    pendientes_sin_identificar = iter(ids_sin_identificar_con_correo)
    for k, b in enumerate(correos.borradores(mes), start=1):
        caso_id = id_por_cedula.get(b["cedula"]) if b["cedula"] else next(pendientes_sin_identificar, None)
        lista_correos.append({
            "id": f"m-{k:02d}", "caso": caso_id, "para": b["para"], "causal": b["causal"],
            "asunto": b["asunto"], "cuerpo": b["cuerpo"],
            "cifras": sorted(verificador.cifras(b["asunto"] + "\n" + b["cuerpo"])),
        })

    return {
        "version": VERSION,
        "periodo": mes.periodo,
        "generado": generado.isoformat(),
        "fecha_limite": mes.fecha_limite.isoformat(),
        "indicadores": _indicadores(mes, hoy),
        "casos": casos,
        "correos": lista_correos,
        "resumen": {"texto": None, "origen": None},
    }


def escribir(mes: Mes, ruta: str | Path, generado: datetime | None = None, hoy: date | None = None) -> Path:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos = construir(mes, generado, hoy)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return ruta
