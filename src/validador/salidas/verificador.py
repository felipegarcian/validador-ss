"""Verificador de cifras (docs/TABLERO.md, sección 6).

Ningún texto que llega al tablero o a un prestador puede traer cifras que no salieron de la
validación. Se usa en dos momentos:

- Antes de enviar un correo aprobado: el texto, aunque la analista lo haya editado, debe traer
  exactamente las mismas cifras del borrador original (`conserva_cifras`).
- Antes de mostrar un texto generado con IA: no puede traer cifras que no estaban en los datos
  que se le enviaron (`sin_cifras_nuevas`).

Cifras son montos en pesos ($1.600.000), porcentajes (1,044 %) y fechas (09/11/2026). Con
`enteros=True` también cuentan los números sueltos (7 de 12 prestadores).
"""
from __future__ import annotations

import re

_PESOS = r"\$\s?-?\d{1,3}(?:\.\d{3})+(?!\d)|\$\s?-?\d+"
_PORCENTAJE = r"-?\d+(?:,\d+)?\s?%"
_FECHA = r"\b\d{1,2}/\d{1,2}/\d{4}\b"
CIFRA = re.compile(f"{_PESOS}|{_PORCENTAJE}|{_FECHA}")
ENTERO = re.compile(r"(?<![\w$])-?\d+(?:[.,]\d+)*(?![\w%])")


def _normalizar(cifra: str) -> str:
    return re.sub(r"\s+", "", cifra)


def cifras(texto: str, enteros: bool = False) -> set[str]:
    """Las cifras del texto, sin espacios internos: «$ 1.600.000» y «$1.600.000» son la misma."""
    encontradas = {_normalizar(c) for c in CIFRA.findall(texto or "")}
    if enteros:
        resto = CIFRA.sub(" ", texto or "")
        encontradas |= {c.rstrip(".,") for c in ENTERO.findall(resto)}
    return encontradas


def conserva_cifras(texto: str, originales: set[str] | list[str]) -> bool:
    """True si el texto trae exactamente las cifras del borrador: ni nuevas ni faltantes."""
    return cifras(texto) == {_normalizar(c) for c in originales}


def sin_cifras_nuevas(texto: str, permitidas: set[str] | list[str], enteros: bool = True) -> bool:
    """True si todas las cifras del texto están entre las permitidas (para textos de IA)."""
    return cifras(texto, enteros) <= {_normalizar(str(c)) for c in permitidas}


def cifras_nuevas(texto: str, permitidas: set[str] | list[str], enteros: bool = True) -> set[str]:
    """Las cifras que sobran, para dejarlas en la Bitácora cuando un texto se descarta."""
    return cifras(texto, enteros) - {_normalizar(str(c)) for c in permitidas}
