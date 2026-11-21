"""Reglas de validación del procedimiento de AZA (v3.0). Código determinista.

Orden de las validaciones (procedimiento 4.4 a 4.6):
  1. Es una planilla           -> si no, PLANILLA INCORRECTA
  2. Está en la Base           -> si no, REVISIÓN MANUAL (I-01)
  3. Tiene honorarios          -> si no, SIN HONORARIOS
  4. Periodo de cotización = N -> si no, OTRO PERIODO
  5. Dice PAGADO               -> si no, PLANILLA INCORRECTA
  6. Documento = cédula, independiente -> si no, PLANILLA INCORRECTA
  7. Tipo de cotizante 59      -> si no, REVISIÓN MANUAL
  8. IBC pagado vs requerido   -> OK / PAGO DE MÁS / PENDIENTE AJUSTE
  Riesgo ARL distinto, IBC desiguales, intereses de mora: solo observaciones.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .esquema import Estado, Expectativa, Reglas, Resultado, Soporte, al_peso


def cargar_reglas(ruta: str | Path) -> Reglas:
    datos = yaml.safe_load(Path(ruta).read_text(encoding="utf-8")) or {}
    return Reglas(**(datos.get("reglas") or {}))


def clasificar(diferencia: int, reglas: Reglas) -> Estado:
    if diferencia > 0:
        return Estado.PAGO_DE_MAS
    if diferencia >= -reglas.tolerancia_abajo:
        return Estado.OK
    return Estado.PENDIENTE_AJUSTE


def _observaciones(s: Soporte, exp: Expectativa, periodo: str, reglas: Reglas) -> tuple[list[str], bool]:
    obs: list[str] = []
    ibcs = {s.ibc_pension, s.ibc_salud, s.ibc_riesgos}
    if None not in ibcs and len(ibcs) > 1:
        obs.append(f"IBC distintos: pensión {s.ibc_pension}, salud {s.ibc_salud}, riesgos {s.ibc_riesgos}.")
    aviso = False
    esperada = reglas.tarifa_arl.get(exp.riesgo)
    if s.tarifa_arl is not None and esperada is not None and abs(s.tarifa_arl - esperada) > 1e-6:
        aviso = True
        obs.append(f"ARL pagada con tarifa {s.tarifa_arl:.3f} %; su riesgo {exp.riesgo} es {esperada:.3f} %.")
    if s.intereses_mora:
        obs.append(f"La planilla trae intereses de mora por {s.intereses_mora}.")
    if s.fecha_pago and s.periodo == periodo:
        anio, mes = (int(x) for x in periodo.split("-"))
        inicio_siguiente = date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)
        if s.fecha_pago < inicio_siguiente:  # mes vencido: el periodo N se paga en N+1
            obs.append("Pagada antes de terminar el mes del periodo (¿mes anticipado?).")
    if exp.especial:
        obs.append("Prestador marcado como Especial.")
    return obs, aviso


def evaluar(
    soporte: Soporte,
    esperado: Expectativa | None,
    periodo: str,
    reglas: Reglas,
    recibido: date | None = None,
    fecha_limite: date | None = None,
    ibc_previo: int = 0,
) -> Resultado:
    """Estado de una planilla frente a la fila del prestador en la Base.

    ibc_previo: IBC de la planilla original cuando esta es una planilla de ajuste (4.8).
    """
    tardio = bool(recibido and fecha_limite and recibido > fecha_limite)

    def res(estado: Estado, motivo: str, **kw) -> Resultado:
        return Resultado(estado=estado, motivo=motivo, tardio=tardio, **kw)

    if not soporte.es_planilla:
        return res(Estado.PLANILLA_INCORRECTA, "El documento no es una planilla de seguridad social.")
    if esperado is None:
        return res(Estado.REVISION_MANUAL, "La persona no está en la Base del mes.", codigo_error="I-01")
    requerido = reglas.ibc_requerido(esperado)
    if requerido is None:
        return res(Estado.SIN_HONORARIOS, "No tuvo honorarios en el mes.")
    if soporte.periodo is None:
        return res(Estado.REVISION_MANUAL, "No se pudo leer el periodo de cotización.", codigo_error="L-03")
    if soporte.periodo != periodo:
        return res(Estado.OTRO_PERIODO, f"La planilla es del periodo {soporte.periodo}; se esperaba {periodo}.")
    if soporte.pagado is not True:
        return res(Estado.PLANILLA_INCORRECTA, "La planilla no aparece como pagada.")
    if soporte.cedula and soporte.cedula != esperado.cedula:
        return res(Estado.PLANILLA_INCORRECTA, "El documento de la planilla no coincide con la cédula de la Base.")
    if (soporte.tipo_empresa and soporte.tipo_empresa.upper() != "INDEPENDIENTE") or soporte.tipo_planilla == "E":
        return res(Estado.PLANILLA_INCORRECTA, "La planilla no es de independiente.")
    if soporte.tipo_cotizante and soporte.tipo_cotizante != reglas.tipo_cotizante:
        return res(Estado.REVISION_MANUAL, f"Tipo de cotizante {soporte.tipo_cotizante}; se esperaba "
                   f"{reglas.tipo_cotizante}.", ibc_requerido=requerido, codigo_error="R-01")
    if soporte.ibc_pagado is None:
        return res(Estado.REVISION_MANUAL, "La planilla no muestra los tres IBC.", codigo_error="L-03",
                   ibc_requerido=requerido)

    pagado = soporte.ibc_pagado + ibc_previo
    diferencia = pagado - requerido
    obs, aviso = _observaciones(soporte, esperado, periodo, reglas)
    estado = clasificar(diferencia, reglas)
    if ibc_previo and estado in (Estado.OK, Estado.PAGO_DE_MAS):
        estado = Estado.AJUSTADO
    datos = dict(ibc_requerido=requerido, ibc_pagado=pagado, diferencia=diferencia,
                 observaciones=obs, aviso_riesgo=aviso)

    if esperado.especial and reglas.especial_a_revision:
        return res(Estado.REVISION_MANUAL, f"Especial: el cálculo da {estado.value}; lo confirma la analista.",
                   codigo_error="R-02", **datos)
    motivos = {
        Estado.OK: "Pagó el IBC requerido.",
        Estado.PAGO_DE_MAS: "Pagó por encima del IBC requerido; se registra para retención en la fuente.",
        Estado.PENDIENTE_AJUSTE: f"Pagó {abs(diferencia):,} de IBC por debajo del requerido.".replace(",", "."),
        Estado.AJUSTADO: "Con la planilla de ajuste cumple el IBC requerido.",
    }
    return res(estado, motivos[estado], **datos)


def calcular_ajuste(requerido: int, pagado: int, riesgo: str, reglas: Reglas) -> dict[str, dict[str, int]]:
    """Tabla de la sección 6: requerido (A), pagado (B) y ajuste (A − B) por concepto."""
    tarifas = {"Pensión": reglas.tarifa_pension, "Salud": reglas.tarifa_salud,
               "ARL": reglas.tarifa_arl[riesgo] / 100}
    filas = {"IBC": {"requerido": requerido, "pagado": pagado, "ajuste": requerido - pagado}}
    for concepto, t in tarifas.items():
        a, b = al_peso(requerido * t), al_peso(pagado * t)
        filas[concepto] = {"requerido": a, "pagado": b, "ajuste": a - b}
    filas["Total"] = {k: sum(filas[c][k] for c in tarifas) for k in ("requerido", "pagado", "ajuste")}
    return filas
