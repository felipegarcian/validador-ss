"""PDF con contraseña: la clave suele ser la cédula de la persona.

En los insumos de AZA, 6 de 7 PDF venían cifrados pero abrían sin clave (solo
restricciones de impresión/copia). Por eso se prueba primero sin clave.

Orden de prueba:
0. Sin clave.
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
    por_nombre = sorted(expectativas.values(),
                        key=lambda e: puntaje_nombre(e.nombre, nombre_remitente or ""), reverse=True)
    for exp in por_nombre:
        agregar(exp.cedula)
    return orden


def _norm(texto: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


def puntaje_nombre(nombre_base: str, nombre_otro: str) -> float:
    """Parecido entre un nombre completo de la Base y un nombre corto o con errores.

    'Ana Gmez' vs 'Ana María Gómez' y 'Juliana Lozano' vs 'Marion Juliana Lozano Muñoz'
    deben puntuar alto; token_set_ratio tolera palabras de más y partial errores de tipeo.
    """
    a, b = _norm(nombre_base), _norm(nombre_otro)
    return 0.6 * fuzz.token_set_ratio(a, b) + 0.4 * fuzz.token_sort_ratio(a, b)


def identificar(nombre: str, expectativas: dict[str, Expectativa],
                minimo: float = 70, margen: float = 8) -> str | None:
    """Cédula de la Base cuyo nombre se parece al dado; None si no hay o es ambiguo."""
    if not (nombre or "").strip() or not expectativas:
        return None
    ranking = sorted(((puntaje_nombre(e.nombre, nombre), c) for c, e in expectativas.items()), reverse=True)
    mejor = ranking[0]
    segundo = ranking[1][0] if len(ranking) > 1 else 0
    if mejor[0] >= minimo and mejor[0] - segundo >= margen:
        return mejor[1]
    return None


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
