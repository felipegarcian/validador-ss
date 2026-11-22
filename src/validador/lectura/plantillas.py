"""Carril 1: lectura por plantillas de formatos conocidos.

Cada plantilla reconoce el texto de un operador y devuelve un Soporte. Si ninguna lo
reconoce, el proceso sigue por el carril 2 (Claude) o va a REVISIÓN MANUAL.

Formatos vistos en los insumos de AZA (noviembre 2026):
  - SuAporte / Enlace Operativo, "AUTOLIQUIDACION CONSOLIDADA": el más común.
  - Enlace Operativo, "Información de la Planilla Pagada": comprobante de pago sin IBC.
  - Compensar, "PLANILLA INTEGRADA DE AUTOLIQUIDACION": vino una pre-planilla sin pagar.
Las pruebas usan textos ficticios con la misma estructura (tests/fixtures).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Callable

from ..esquema import Soporte

MESES = {m: i for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                       "septiembre", "octubre", "noviembre", "diciembre"], start=1)}
_PESOS = re.compile(r"\$\s*([\d.]+)")


@dataclass
class Plantilla:
    operador: str
    reconoce: Callable[[str], bool]
    extraer: Callable[[str], Soporte]


def _numero(texto: str | None) -> int | None:
    digitos = re.sub(r"\D", "", texto or "")
    return int(digitos) if digitos else None


def _campo(patron: str, texto: str, flags: int = re.IGNORECASE) -> str | None:
    m = re.search(patron, texto, flags)
    return m.group(1).strip() if m else None


def _periodo_texto(valor: str | None) -> str | None:
    """'octubre de 2026' -> '2026-10'."""
    m = re.match(r"([a-záéíóú]+)\s+de\s+(\d{4})", (valor or "").lower())
    if not m or m.group(1) not in MESES:
        return None
    return f"{m.group(2)}-{MESES[m.group(1)]:02d}"


# --- SuAporte: AUTOLIQUIDACION CONSOLIDADA ---------------------------------------------------

def _extraer_suaporte(texto: str) -> Soporte:
    pagado = re.search(r"\bPAGADO\s+(\d{2})/(\d{2})/(\d{4})", texto)
    cedula = _campo(r"Documento\s+(?:CC|CE|PA|TI)\s*(\d+)", texto)
    # Línea de detalle del afiliado: "CC <doc> <nombre revuelto> <tipo cotizante> 00 ..."
    detalle = _campo(rf"^((?:CC|CE)\s+{cedula}\s.*)$", texto, re.MULTILINE) if cedula else None
    tipo_cot = _campo(r"\s(\d{2})\s00\s", detalle or "", 0)
    tarifa = _campo(r"\s(\d,\d{3})\s", detalle or "", 0)
    # III. TOTALES: la primera línea de solo pesos trae IBC pensión, salud, riesgos, cajas, aportes...
    totales = None
    bloque = texto.split("III.TOTALES", 1)[-1] if "III.TOTALES" in texto else ""
    for linea in bloque.splitlines():
        if linea.strip().startswith("$"):
            totales = [int(v.replace(".", "")) for v in _PESOS.findall(linea)]
            break
    ibc_p = ibc_s = ibc_r = mora = total = None
    if totales and len(totales) >= 6:
        ibc_p, ibc_s, ibc_r = totales[0], totales[1], totales[2]
        total, mora = totales[-1], totales[-2]
    return Soporte(
        operador="SuAporte",
        numero_planilla=_campo(r"N[uú]m[eé]ro Planilla:\s*(\d+)", texto),
        periodo=_periodo_texto(_campo(r"Periodo Cotizaci[oó]n:\s*([a-záéíóú]+ de \d{4})", texto)),
        pagado=bool(pagado),
        fecha_pago=date(int(pagado.group(3)), int(pagado.group(2)), int(pagado.group(1))) if pagado else None,
        nombre=_campo(r"Raz[oó]n Social\s+(.+)", texto),
        cedula=cedula,
        tipo_empresa=_campo(r"Tipo de Empresa\s+(\w+)", texto),
        tipo_planilla=_campo(r"Tipo Planilla:\s*(\w+)", texto),
        tipo_cotizante=tipo_cot,
        tarifa_arl=float(tarifa.replace(",", ".")) if tarifa else None,
        ibc_pension=ibc_p, ibc_salud=ibc_s, ibc_riesgos=ibc_r,
        intereses_mora=mora, valor_total=total,
    )


# --- Enlace Operativo: comprobante de pago (no trae IBC) -------------------------------------

def _extraer_comprobante_enlace(texto: str) -> Soporte:
    fecha = _campo(r"^Fecha\s+(\d{4}-\d{2}-\d{2})", texto, re.MULTILINE)
    return Soporte(
        operador="Enlace Operativo (comprobante)",
        numero_planilla=_campo(r"N[uú]mero Planilla\s+(\d+)", texto),
        periodo=_periodo_texto(_campo(r"Periodo de Cotizaci[oó]n Otros Riesgos\s+([a-záéíóú]+ de \d{4})", texto)),
        pagado=(_campo(r"Estado de la Transacci[oó]n\s+(\w+)", texto) or "").lower() == "aprobada",
        fecha_pago=date.fromisoformat(fecha) if fecha else None,
        nombre=_campo(r"^Empresa\s+(.+)$", texto, re.MULTILINE),
        cedula=_campo(r"(?:CC|CEDULA CIUDADANIA CC)\s+(\d{6,})", texto),
        tipo_planilla=_campo(r"Tipo de Planilla\s+(\w+)", texto),
        valor_total=_numero(_campo(r"Total a Pagar:\s*\$\s*([\d.]+)", texto)),
    )


# --- Compensar: planilla integrada (pre-planilla si no trae fecha de pago) -------------------

def _extraer_compensar(texto: str) -> Soporte:
    linea = re.search(r"(\d{4}-\d{2})\s+(\d{4}-\d{2})\s+([A-Z])\s+\$", texto)  # periodo salud, pensión, tipo
    ibcs = [int(v.replace(".", "")) for v in re.findall(r"(\d{1,3}(?:\.\d{3})+)\s30\b", texto)]
    pagada = bool(re.search(r"\bPAGAD[OA]\b|FECHA DE PAGO\s*:?\s*\d", texto, re.IGNORECASE))
    return Soporte(
        operador="Compensar",
        periodo=linea.group(2) if linea else None,
        tipo_planilla=linea.group(3) if linea else None,
        cedula=_campo(r"^CC\s+(\d{6,})", texto, re.MULTILINE),
        pagado=pagada,
        ibc_pension=ibcs[0] if len(ibcs) > 0 else None,
        ibc_salud=ibcs[1] if len(ibcs) > 1 else None,
        ibc_riesgos=ibcs[2] if len(ibcs) > 2 else None,
        valor_total=_numero(_campo(r"TOTAL A PAGAR\s*\n.*\$([\d.]+)\s*$", texto, re.IGNORECASE | re.MULTILINE)),
    )


REGISTRO: list[Plantilla] = [
    Plantilla("SuAporte", lambda t: "AUTOLIQUIDACION" in t and "CONSOLIDADA" in t and "III.TOTALES" in t,
              _extraer_suaporte),
    Plantilla("Enlace Operativo (comprobante)", lambda t: "Información de la Planilla Pagada" in t,
              _extraer_comprobante_enlace),
    Plantilla("Compensar", lambda t: "PLANILLA INTEGRADA DE AUTOLIQUIDACION" in t.upper()
              and "COMPENSAR" in t.upper(), _extraer_compensar),
]


def leer(texto: str) -> Soporte | None:
    """Devuelve el Soporte si alguna plantilla reconoce el texto; None si hay que ir al carril 2."""
    for plantilla in REGISTRO:
        if plantilla.reconoce(texto):
            return plantilla.extraer(texto)
    return None


# --- Plantillas en YAML (propuestas por Claude, probadas y aprobadas por TI) ------------------

TIPOS = {
    "texto": lambda v: v.strip(),
    "pesos": lambda v: _numero(v),
    "decimal": lambda v: float(v.replace(".", "").replace(",", ".")) if "," in v else float(v),
    "periodo_texto": _periodo_texto,
    "periodo_iso": lambda v: v if re.fullmatch(r"\d{4}-\d{2}", v) else None,
    "fecha_dmy": lambda v: date(int(v[6:10]), int(v[3:5]), int(v[0:2])),
    "fecha_iso": lambda v: date.fromisoformat(v[:10]),
}
CAMPOS_PERMITIDOS = set(Soporte.model_fields) - {"origen_lectura"}


def plantilla_desde_yaml(definicion: dict) -> Plantilla:
    """Valida la definición y la convierte en Plantilla. Lanza ValueError con un motivo claro."""
    for clave in ("operador", "reconoce", "campos"):
        if not definicion.get(clave):
            raise ValueError(f"La plantilla no tiene «{clave}».")
    reconoce = [str(x) for x in definicion["reconoce"]]
    campos = {}
    for campo, regla in definicion["campos"].items():
        if campo not in CAMPOS_PERMITIDOS:
            raise ValueError(f"Campo desconocido «{campo}».")
        tipo = regla.get("tipo", "texto")
        if tipo != "existe" and tipo not in TIPOS:
            raise ValueError(f"Tipo desconocido «{tipo}» en «{campo}».")
        patron = re.compile(regla["regex"], re.IGNORECASE | re.MULTILINE)
        if tipo != "existe" and patron.groups != 1:
            raise ValueError(f"El regex de «{campo}» debe tener exactamente un grupo de captura.")
        campos[campo] = (patron, tipo)

    def extraer(texto: str) -> Soporte:
        datos: dict = {"operador": definicion["operador"]}
        for campo, (patron, tipo) in campos.items():
            m = patron.search(texto)
            if tipo == "existe":
                datos[campo] = bool(m)
            elif m:
                try:
                    datos[campo] = TIPOS[tipo](m.group(1))
                except (ValueError, IndexError):
                    datos[campo] = None
        return Soporte(**datos)

    return Plantilla(definicion["operador"], lambda t: all(r in t for r in reconoce), extraer)


def cargar_plantillas_yaml(carpeta: str | None = None, incluir_borradores: bool = False) -> list[Plantilla]:
    """Lee plantillas_operador/*.yaml. Solo las de estado «activa» entran al carril 1."""
    import yaml
    from pathlib import Path
    base = Path(carpeta) if carpeta else Path(__file__).resolve().parents[3] / "plantillas_operador"
    salida = []
    for archivo in sorted(base.glob("*.yaml")):
        definicion = yaml.safe_load(archivo.read_text(encoding="utf-8")) or {}
        if definicion.get("estado") == "activa" or incluir_borradores:
            salida.append(plantilla_desde_yaml(definicion))
    return salida


try:
    REGISTRO.extend(cargar_plantillas_yaml())
except Exception:  # una plantilla mal escrita no debe tumbar el motor: se reporta en las pruebas
    pass
