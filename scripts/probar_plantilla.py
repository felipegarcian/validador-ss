"""Prueba una plantilla YAML contra un caso que ya leyó Claude, antes de activarla.

Uso:  python -I scripts/probar_plantilla.py plantilla.yaml texto_planilla.txt respuesta_claude.txt

Imprime campo por campo si la plantilla obtiene el mismo valor que la respuesta confirmada.
Sale con código 0 solo si todos coinciden.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from validador.lectura import carril2_asistido as c2  # noqa: E402
from validador.lectura.plantillas import plantilla_desde_yaml  # noqa: E402

CAMPOS = ["periodo", "pagado", "tipo_planilla", "tipo_cotizante", "ibc_pension", "ibc_salud",
          "ibc_riesgos", "tarifa_arl", "intereses_mora", "fecha_pago", "numero_planilla"]


def main() -> int:
    ruta_yaml, ruta_texto, ruta_resp = (Path(x) for x in sys.argv[1:4])
    try:
        plantilla = plantilla_desde_yaml(yaml.safe_load(ruta_yaml.read_text(encoding="utf-8")))
    except ValueError as e:
        print(f"La plantilla no es válida: {e}")
        return 1
    texto = ruta_texto.read_text(encoding="utf-8")
    if not plantilla.reconoce(texto):
        print("La plantilla no reconoce este documento: revisa la lista «reconoce».")
        return 1
    leido = plantilla.extraer(texto)
    confirmado, problemas = c2.leer_respuesta(ruta_resp.read_text(encoding="utf-8"))
    if problemas:
        print("La respuesta confirmada tiene problemas:", *problemas, sep="\n- ")
        return 1
    fallas = 0
    for campo in CAMPOS:
        a, b = getattr(leido, campo), getattr(confirmado, campo)
        if b is None:
            continue
        ok = a == b or (campo == "intereses_mora" and (a or 0) == (b or 0))
        fallas += not ok
        print(f"{'OK ' if ok else 'NO '} {campo:<16} plantilla={a!r:<18} confirmado={b!r}")
    print("\nLista para activar." if not fallas else f"\n{fallas} campo(s) no coinciden: ajusta los regex.")
    return 0 if not fallas else 1


if __name__ == "__main__":
    raise SystemExit(main())
