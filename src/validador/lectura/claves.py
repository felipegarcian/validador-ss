"""PDF con contraseña: la clave suele ser la cédula de la persona.

Orden de prueba:
1. Cédula ya conocida del remitente (directorio).
2. Cédulas escritas en el correo, primero las que están en la liquidación.
3. Cédulas de la liquidación ordenadas por parecido con el nombre del remitente.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from ..esquema import Expectativa

_NUMERO = re.compile(r"\b\d[\d.\s]{5,13}\d\b")


def cedulas_en_texto(texto: str) -> list[str]:
    vistos: list[str] = []
    for bruto in _NUMERO.findall(texto or ""):
        numero = re.sub(r"\D", "", bruto)
        if 6 <= len(numero) <= 10 and numero not in vistos:
            vistos.append(numero)
    return vistos


def candidatos_clave(
    texto_correo: str,
    nombre_remitente: str,
    expectativas: dict[str, Expectativa],
    cedula_conocida: str | None = None,
) -> list[str]:
    orden: list[str] = []

    def agregar(cedula: str) -> None:
        if cedula and cedula not in orden:
            orden.append(cedula)

    if cedula_conocida:
        agregar(cedula_conocida)
    en_texto = cedulas_en_texto(texto_correo)
    for cedula in en_texto:
        if cedula in expectativas:
            agregar(cedula)
    for cedula in en_texto:
        agregar(cedula)
    por_nombre = sorted(
        expectativas.values(),
        key=lambda e: fuzz.token_sort_ratio(e.nombre.lower(), (nombre_remitente or "").lower()),
        reverse=True,
    )
    for exp in por_nombre:
        agregar(exp.cedula)
    return orden


def abrir_con_clave(ruta_pdf: str, candidatos: list[str]):
    """Devuelve (pdf_abierto, clave) o (None, None). La clave que abre identifica a la persona."""
    import pdfplumber  # se importa aquí para que las pruebas no lo exijan

    for clave in [None, *candidatos]:
        try:
            pdf = pdfplumber.open(ruta_pdf, password=clave or "")
            _ = pdf.pages[0]
            return pdf, clave
        except Exception:
            continue
    return None, None
