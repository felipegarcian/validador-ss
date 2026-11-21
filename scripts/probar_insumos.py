"""Corre el validador sobre insumos reales en una carpeta local (nunca en el repo).

Uso:  python -I scripts/probar_insumos.py datos_reales/2026-10 --periodo 2026-10 [--base "archivo.xlsx"] [--base-anonimizada]

La carpeta debe traer la Base (*.xlsx que contenga "Base") y los PDF. Como aún no hay
correos, el remitente se toma del nombre del archivo ("Ana Gomez.pdf"). Si junto al PDF hay
un "Ana Gomez.txt" o "Ana Gomez.eml" con el texto del correo, de ahí se toman las cédulas
para la contraseña y la dirección del remitente (la primera que aparezca).
Imprime una fila por PDF, compara con lo que la analista dejó en IBC PAGADO y lista los
borradores de correo que pide la contraseña (L-04). Deja en la misma carpeta la copia
diligenciada de la Base, el Control del mes y, si hay ajustes, el Formato de Ajuste.
No cierra el corte: quien no tenga PDF en la carpeta queda como estaba en la Base.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from validador.conciliacion import Mes  # noqa: E402
from validador.esquema import Estado  # noqa: E402
from validador.expectativas import cargar_base, limpiar_cedula, ubicar_columnas  # noqa: E402
from validador.lectura import plantillas  # noqa: E402
from validador.lectura.claves import abrir_con_clave, candidatos_clave  # noqa: E402
from validador.salidas import archivos_aza, correos, excel_maestro  # noqa: E402

_DIRECCION = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def correo_junto_al(pdf: Path) -> tuple[str, str]:
    """(texto del correo, dirección del remitente) desde un .txt/.eml con el mismo nombre del PDF."""
    for ext in (".txt", ".eml"):
        ruta = pdf.with_suffix(ext)
        if ruta.exists():
            texto = ruta.read_text(encoding="utf-8", errors="replace")
            direccion = _DIRECCION.search(texto)
            return texto, direccion.group(0) if direccion else ""
    return "", ""


def ibc_analista(ruta_base: Path) -> dict[str, object]:
    from openpyxl import load_workbook
    hoja = load_workbook(ruta_base, data_only=True).worksheets[0]
    fila, pos = ubicar_columnas(hoja)
    if "ibc_pagado" not in pos:
        return {}
    return {limpiar_cedula(r[pos["cedula"]]): r[pos["ibc_pagado"]]
            for r in hoja.iter_rows(min_row=fila + 1, values_only=True) if r[pos["cedula"]]}


def main() -> None:
    sys.stdout.reconfigure(errors="replace")  # la consola de Windows (cp1252) no imprime todos los caracteres
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--periodo", required=True)
    ap.add_argument("--base-anonimizada", action="store_true",
                    help="La Base trae cédulas de prueba: no comparar el documento de la planilla")
    ap.add_argument("--base", help="Nombre del archivo de la Base dentro de la carpeta, si hay más de uno")
    a = ap.parse_args()
    carpeta = Path(a.carpeta)
    if a.base:
        ruta_base = carpeta / a.base
    else:
        bases = [p for p in sorted(carpeta.glob("*.xlsx"))
                 if "base" in p.name.lower() and "diligenciada" not in p.name.lower()]
        if len(bases) != 1:
            sys.exit(f"Hay {len(bases)} Bases en la carpeta; indica cuál con --base: {[p.name for p in bases]}")
        ruta_base = bases[0]
    exps = cargar_base(ruta_base)
    analista = ibc_analista(ruta_base)
    mes = Mes(periodo=a.periodo, expectativas=exps, validar_documento=not a.base_anonimizada)
    print(f"Base: {len(exps)} prestadores · fecha límite {mes.fecha_limite}\n")
    print(f"{'archivo':<42} {'abre':<9} {'operador':<16} {'estado':<20} {'IBC req':>11} {'IBC pag':>11} "
          f"{'analista':>11}  observaciones")
    for pdf in sorted(carpeta.glob("*.pdf")):
        remitente = pdf.stem
        texto_correo, correo_remitente = correo_junto_al(pdf)
        conocida = mes.identificar_remitente(remitente, correo_remitente)
        abierto, clave = abrir_con_clave(
            str(pdf), candidatos_clave(texto_correo, remitente, exps, cedula_conocida=conocida)[:5])
        if abierto is None:
            cedula, r = mes.recibir_sin_abrir(remitente=remitente, correo_remitente=correo_remitente,
                                              archivo=pdf.name)
            quien = "identificado" if cedula else "SIN IDENTIFICAR"
            print(f"{pdf.name[:42]:<42} {'NO':<9} {'':<16} {r.estado.value:<20} {r.ibc_requerido or '':>11} "
                  f"{'':>11} {'':>11}  {r.codigo_error} {r.motivo} ({quien})")
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
    pedir_clave = [b for b in correos.borradores(mes) if b["causal"] == "4.3"]
    if pedir_clave:
        print(f"\nBorradores que piden la contraseña (L-04): {len(pedir_clave)}")
        for b in pedir_clave:
            en_base = b["cedula"] and exps[b["cedula"]].correo
            destino = "dirección de la Base" if en_base else "dirección del remitente"
            print(f"  - {b['asunto']} | para: {destino}{'' if b['para'] else ' (SIN DIRECCIÓN: completar a mano)'}")

    # Salidas en la misma carpeta del mes. La Base original no se toca: se escribe una copia.
    copia = archivos_aza.escribir_base(ruta_base, mes, carpeta / f"{ruta_base.stem} (diligenciada).xlsx")
    control = excel_maestro.escribir(mes, carpeta / f"Control_SS_{a.periodo}.xlsx")
    ajuste = archivos_aza.escribir_formato_ajuste(mes, carpeta / f"Formato Ajuste Seguridad social {a.periodo}.xlsx")
    print("\nSalidas:")
    for ruta in (copia, control, ajuste):
        if ruta:
            print(f"  - {ruta}")
    if not ajuste:
        print("  (sin Formato de Ajuste: nadie quedó en PENDIENTE AJUSTE)")


if __name__ == "__main__":
    main()
