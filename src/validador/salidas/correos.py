"""Borradores de correo. El texto sale de plantillas editables; las cifras, de la validación."""
from __future__ import annotations

from ..esquema import Estado, Expectativa, Resultado, Soporte

PLANTILLAS: dict[Estado, str] = {
    Estado.PAGO_MENOR: (
        "Recibimos tu soporte de seguridad social de {mes}. Al compararlo con tu liquidación "
        "encontramos una diferencia.\n\nValor esperado: {esperado}\nValor pagado en tu soporte: {pagado}\n"
        "Diferencia: {diferencia}\n\nPor favor paga el excedente y responde con el nuevo soporte."
    ),
    Estado.SIN_PAGO: "El soporte que enviaste de {mes} no muestra el pago realizado. "
                     "Por favor envía la planilla con el pago confirmado.",
    Estado.MES_O_ARCHIVO_ERRADO: "El archivo que recibimos no corresponde al soporte de seguridad social "
                                 "de {mes}. Por favor envía el comprobante correcto.",
    Estado.ESPERADO: "Aún no recibimos tu soporte de seguridad social de {mes}. "
                     "El plazo vence el quinto día hábil.",
    Estado.NO_ENTREGO: "No recibimos tu soporte de seguridad social de {mes} dentro del plazo. "
                       "Por favor envíalo cuanto antes.",
}


def pesos(valor: int | None) -> str:
    return "" if valor is None else "$ " + f"{valor:,}".replace(",", ".")


def redactar(resultado: Resultado, esperado: Expectativa, mes: str,
             soporte: Soporte | None = None, plantillas: dict[Estado, str] | None = None) -> tuple[str, str] | None:
    """Devuelve (asunto, cuerpo) o None si el estado no lleva correo. Nunca envía."""
    texto = (plantillas or PLANTILLAS).get(resultado.estado)
    if texto is None:
        return None
    pagado = soporte.valor_pagado if soporte else None
    cuerpo = texto.format(
        nombre=esperado.nombre, mes=mes, esperado=pesos(esperado.valor_esperado), pagado=pesos(pagado),
        diferencia=pesos(abs(resultado.diferencia)) if resultado.diferencia is not None else "",
    )
    asunto = f"Seguridad social {mes}"
    return asunto, f"Hola, {esperado.nombre}:\n\n{cuerpo}\n\nGestión Humana, AZA Gestión del Riesgo"
