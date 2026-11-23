"""Carril 2 automático por API (opcional, para más adelante).

Hoy el carril 2 funciona sin API: ver lectura/carril2_asistido.py y docs/CARRIL2_CLAUDE.md.
Este módulo queda para cuando AZA tenga acceso por API. Diseño:

Paso 1, identificar: Claude recibe solo el PDF que falló y devuelve los campos del
esquema Soporte. Pasa por el mismo autochequeo y las mismas reglas. Queda marcado
origen_lectura="ia" en la bitácora.

Paso 2, generar la plantilla: Claude propone la plantilla del formato nuevo.
No se activa sola: debe pasar las pruebas automáticas y una aprobación de TI.
Desde ahí ese formato se lee por el carril 1 y no consume tokens.

Requisitos por confirmar con AZA: acceso a Claude por API y condiciones de datos.
Se activa con la variable de entorno CLAUDE_HABILITADO=1 y ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import os

from ..esquema import Soporte


def habilitado() -> bool:
    return os.environ.get("CLAUDE_HABILITADO") == "1" and bool(os.environ.get("ANTHROPIC_API_KEY"))


def identificar(pdf_bytes: bytes) -> Soporte:
    raise NotImplementedError("Carril 2 sin implementar: el caso va a revisión manual (código L-01).")


def proponer_plantilla(pdf_bytes: bytes, soporte: Soporte) -> str:
    raise NotImplementedError("Generación de plantillas sin implementar.")
