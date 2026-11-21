"""Borradores de correo con las causales del procedimiento (sección 7). Nunca envía.

Los textos son editables (Reglas.xlsx o tablero); las cifras salen de la validación.
Todos van a la columna CORREO de la Base o, si está vacía, al directorio de prestadores.
"""
from __future__ import annotations

from datetime import date

from ..esquema import Estado, Expectativa, Reglas, Resultado, Soporte
from ..reglas import calcular_ajuste

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]

# causal: (asunto, cuerpo). Marcadores entre llaves.
PLANTILLAS: dict[str, tuple[str, str]] = {
    "7.1": ("Seguridad Social {Mes} – planilla de otro periodo",
            "la planilla que enviaste corresponde al periodo {periodo_recibido}. El pago es mes vencido, por lo que "
            "debes enviar la planilla del periodo {mes}, pagada a más tardar el {fecha_limite}."),
    "7.2": ("Seguridad Social {Mes} – planilla incorrecta",
            "el documento que enviaste no es una planilla pagada a tu nombre del periodo {mes} "
            "(motivo: {motivo}). Por favor envía la planilla correcta."),
    "7.3": ("Ajuste Seguridad Social {Mes} – {nombre}",
            "según tus honorarios de {mes} por {base}, el IBC requerido es {ibc_requerido}. Tu planilla reporta "
            "{ibc_pagado}.\n\nValor que pagaste: pensión {p_pen}, salud {p_sal}, ARL {p_arl}.\n"
            "Valor del ajuste: pensión {a_pen}, salud {a_sal}, ARL {a_arl}. Total ajuste {a_tot}.\n\n"
            "Envía la planilla de ajuste con el asunto \"Ajuste Seguridad Social {Mes}\". Adjunto: cálculo del ajuste."),
    "7.4": ("Seguridad Social {Mes} – planilla pendiente",
            "no hemos recibido tu planilla del periodo {mes}. El plazo era el {fecha_limite}. Sin ella "
            "Contabilidad no puede autorizar el pago de tus honorarios."),
    "7.5": ("Seguridad Social – clase de riesgo ARL",
            "en tu planilla del periodo {mes} la ARL se pagó con tarifa {tarifa_pagada} %. A partir del próximo pago "
            "debes cotizar con riesgo {riesgo}, que es el que corresponde a tu actividad."),
}
CAUSAL_POR_ESTADO = {Estado.OTRO_PERIODO: "7.1", Estado.PLANILLA_INCORRECTA: "7.2",
                     Estado.PENDIENTE_AJUSTE: "7.3", Estado.NO_ENVIO: "7.4"}


def pesos(valor: int | None) -> str:
    return "" if valor is None else "$" + f"{valor:,}".replace(",", ".")


def nombre_mes(periodo: str) -> str:
    anio, mes = (int(x) for x in periodo.split("-"))
    return f"{MESES[mes - 1]} {anio}"


def redactar(resultado: Resultado, esperado: Expectativa, periodo: str, fecha_limite: date,
             soporte: Soporte | None = None, reglas: Reglas | None = None, causal: str | None = None,
             plantillas: dict[str, tuple[str, str]] | None = None) -> tuple[str, str] | None:
    """Devuelve (asunto, cuerpo) o None si el estado no lleva correo."""
    reglas = reglas or Reglas()
    causal = causal or CAUSAL_POR_ESTADO.get(resultado.estado)
    if causal is None:
        return None
    asunto, cuerpo = (plantillas or PLANTILLAS)[causal]
    mes = nombre_mes(periodo)
    datos = dict(nombre=esperado.nombre.split()[0].title(), mes=mes, Mes=MESES[int(periodo[5:]) - 1].title(),
                 fecha_limite=fecha_limite.strftime("%d/%m/%Y"), motivo=resultado.motivo.rstrip(".").lower(),
                 periodo_recibido=nombre_mes(soporte.periodo) if soporte and soporte.periodo else "otro",
                 base=pesos(esperado.base_rtte), ibc_requerido=pesos(resultado.ibc_requerido),
                 ibc_pagado=pesos(resultado.ibc_pagado), riesgo=esperado.riesgo,
                 tarifa_pagada=f"{soporte.tarifa_arl:.3f}".replace(".", ",") if soporte and soporte.tarifa_arl is not None else "")
    if causal == "7.3" and resultado.ibc_requerido and resultado.ibc_pagado is not None:
        t = calcular_ajuste(resultado.ibc_requerido, resultado.ibc_pagado, esperado.riesgo, reglas)
        datos.update(p_pen=pesos(t["Pensión"]["pagado"]), p_sal=pesos(t["Salud"]["pagado"]),
                     p_arl=pesos(t["ARL"]["pagado"]), a_pen=pesos(t["Pensión"]["ajuste"]),
                     a_sal=pesos(t["Salud"]["ajuste"]), a_arl=pesos(t["ARL"]["ajuste"]),
                     a_tot=pesos(t["Total"]["ajuste"]))
    return asunto.format(**datos), f"Hola {datos['nombre']}: {cuerpo.format(**datos)}\n\nGestión Humana · AZA Gestión del Riesgo"


def borradores(mes, plantillas: dict[str, tuple[str, str]] | None = None) -> list[dict]:
    """Todos los borradores del mes, incluido el aviso de riesgo ARL (7.5) que no cambia el estado."""
    salida = []
    for cedula, r in mes.estados.items():
        exp = mes.expectativas[cedula]
        soporte = (mes.soportes.get(cedula) or [None])[-1]
        for causal in [CAUSAL_POR_ESTADO.get(r.estado), "7.5" if r.aviso_riesgo else None]:
            if causal:
                asunto, cuerpo = redactar(r, exp, mes.periodo, mes.fecha_limite, soporte, mes.reglas, causal, plantillas)
                salida.append({"cedula": cedula, "para": exp.correo or "", "causal": causal,
                               "asunto": asunto, "cuerpo": cuerpo})
    return salida
