"""Días hábiles en Colombia."""
from __future__ import annotations

from datetime import date, timedelta

import holidays


def es_habil(dia: date) -> bool:
    return dia.weekday() < 5 and dia not in holidays.CO(years=dia.year)


def n_esimo_dia_habil(anio: int, mes: int, n: int = 5) -> date:
    """Fecha del n-ésimo día hábil del mes (por defecto el quinto, el corte de entrega)."""
    dia, cuenta = date(anio, mes, 1), 0
    while True:
        if es_habil(dia):
            cuenta += 1
            if cuenta == n:
                return dia
        dia += timedelta(days=1)


def mes_siguiente(periodo: str) -> tuple[int, int]:
    """El soporte del período AAAA-MM se entrega en el mes siguiente."""
    anio, mes = (int(x) for x in periodo.split("-"))
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)
