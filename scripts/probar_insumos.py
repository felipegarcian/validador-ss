"""Corre el validador sobre insumos reales en una carpeta local (nunca en el repo).

Uso:  python -I scripts/probar_insumos.py datos_reales/2026-10 --periodo 2026-10 [--base-anonimizada]

La carpeta debe traer la Base (*.xlsx que contenga "Base") y los PDF. Como aún no hay
correos, el remitente se toma del nombre del archivo ("Ana Gomez.pdf").
Imprime una fila por PDF y compara con lo que la analista dejó en IBC PAGADO.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from validador.conciliacion import Mes  # noqa: E402
from validador.esquema import Estado  # noqa: E402
from validador.expectativas import cargar_base, limpiar_cedula, ubicar_columnas  # noqa: E402
from validador.lectura import plantillas  # noqa: E402
from validador.lectura.claves import abrir_con_clave, candidatos_clave  # noqa: E402


def ibc_analista(ruta_base: Path) -> dict[str, object]:
    from openpyxl import load_workbook
    hoja = load_workbook(ruta_base, data_only=True).worksheets[0]
    fila, pos = ubicar_columnas(hoja)
    if "ibc_pagado" not in pos:
        return {}
    return {limpiar_cedula(r[pos["cedula"]]): r[pos["ibc_pagado"]]
            for r in hoja.iter_rows(min_row=fila + 1, values_only=True) if r[pos["cedula"]]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--periodo", required=True)
    ap.add_argument("--base-anonimizada", action="store_true",
                    help="La Base trae cédulas de prueba: no comparar el documento de la planilla")
    a = ap.parse_args()
    carpeta = Path(a.carpeta)
    ruta_base = next(p for p in carpeta.glob("*.xlsx") if "base" in p.name.lower())
    exps = cargar_base(ruta_base)
    analista = ibc_analista(ruta_base)
    mes = Mes(periodo=a.periodo, expectativas=exps, validar_documento=not a.base_anonimizada)
    print(f"Base: {len(exps)} prestadores · fecha límite {mes.fecha_limite}\n")
    print(f"{'archivo':<42} {'abre':<9} {'operador':<16} {'estado':<20} {'IBC req':>11} {'IBC pag':>11} "
          f"{'analista':>11}  observaciones")
    for pdf in sorted(carpeta.glob("*.pdf")):
        remitente = pdf.stem
        abierto, clave = abrir_con_clave(str(pdf), candidatos_clave("", remitente, exps)[:5])
        if abierto is None:
            print(f"{pdf.name[:42]:<42} {'NO':<9} {'':<16} {'REVISIÓN MANUAL':<20}  (contraseña desconocida)")
            continue
        texto = "\n".join(p.extract_text() or "" for p in abierto.pages)
        abierto.close()
        cedula, r = mes.recibir_texto(texto, remitente=remitente)
        s = plantillas.leer(texto)
        ref = analista.get(cedula or "")
        print(f"{pdf.name[:42]:<42} {'sin clave' if clave is None else 'con clave':<9} "
              f"{(s.operador if s else '-')[:16]:<16} {r.estado.value:<20} {r.ibc_requerido or '':>11} "
              f"{'' if r.ibc_pagado is None else r.ibc_pagado:>11} {'' if ref is None else ref:>11}  "
              f"{r.motivo} {' '.join(r.observaciones)}")
    print("\nResumen:", {k: v for k, v in mes.resumen().items() if k != Estado.ESPERADO.value})


if __name__ == "__main__":
    main()
