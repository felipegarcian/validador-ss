"""Adaptador local para la demo y las pruebas: carpetas en disco en lugar de Office 365.

Estructura esperada:
  <raiz>/01_Entrada/liquidacion_AAAA-MM.xlsx
  <raiz>/buzon/*.txt        (texto de cada comprobante; un archivo por correo)
"""
from __future__ import annotations

from pathlib import Path


def liquidacion(raiz: str | Path) -> tuple[str, Path]:
    archivo = sorted(Path(raiz, "01_Entrada").glob("liquidacion_*.xlsx"))[-1]
    return archivo.stem.split("_")[-1], archivo


def soportes(raiz: str | Path) -> list[tuple[str, str]]:
    return [(p.name, p.read_text(encoding="utf-8")) for p in sorted(Path(raiz, "buzon").glob("*.txt"))]
