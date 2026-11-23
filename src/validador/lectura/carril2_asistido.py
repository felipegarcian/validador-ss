"""Carril 2 asistido: Claude lee el formato nuevo con el plan que AZA ya tiene, sin API.

Cuando ninguna plantilla reconoce una planilla, el sistema prepara un «paquete»:
instrucciones + el texto del PDF con los datos personales tapados. La analista lo
copia, lo pega en el proyecto «Validador SS · Carril 2» de su Claude y pega de vuelta
el bloque JSON que Claude responde. El sistema lo valida con las mismas reglas que el
carril 1 y, si falta algo, dice en palabras simples qué pedirle a Claude.

Por qué así:
- No requiere API ni contrato nuevo: AZA ya usa Claude.
- Minimización de datos: la cédula, el nombre, correos, teléfonos y direcciones se
  tapan antes de copiar. El sistema verifica el documento localmente.
- La decisión sigue siendo determinista: Claude solo transcribe campos; el estado lo
  calcula reglas.py.
- Cada formato se paga una vez: con la respuesta confirmada, un segundo paquete le
  pide a Claude una plantilla YAML que, probada y aprobada, pasa al carril 1.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date

from ..esquema import Expectativa, Soporte

ESQUEMA = {
    "es_planilla": "true si es una planilla de seguridad social (PILA); false si es otra cosa",
    "pagado": "true solo si el documento dice que la planilla está PAGADA; false si es pre-planilla o pendiente",
    "periodo": "periodo de cotización de pensión en formato AAAA-MM",
    "tipo_planilla": "letra del tipo de planilla, por ejemplo I (independiente) o E (empleados)",
    "tipo_empresa": "texto del tipo de aportante, por ejemplo INDEPENDIENTE",
    "tipo_cotizante": "código de dos dígitos del tipo de cotizante, por ejemplo 59",
    "ibc_pension": "IBC de pensión en pesos, número entero sin puntos",
    "ibc_salud": "IBC de salud en pesos, número entero sin puntos",
    "ibc_riesgos": "IBC de riesgos laborales (ARL) en pesos, número entero sin puntos",
    "tarifa_arl": "tarifa de ARL en porcentaje como número decimal, por ejemplo 1.044",
    "intereses_mora": "intereses de mora en pesos, 0 si no hay",
    "fecha_pago": "fecha de pago en formato AAAA-MM-DD, null si no aparece",
    "operador": "nombre del operador de información (SOI, Aportes en Línea, Mi Planilla...)",
    "numero_planilla": "número de la planilla",
}
OBLIGATORIOS = ["es_planilla", "pagado", "periodo", "ibc_pension", "ibc_salud", "ibc_riesgos"]

AYUDA = {
    "periodo": "el periodo de cotización (mes y año que se está pagando)",
    "pagado": "si la planilla aparece como PAGADA",
    "ibc_pension": "el IBC de pensión (suele estar en la sección de totales)",
    "ibc_salud": "el IBC de salud (suele estar en la sección de totales)",
    "ibc_riesgos": "el IBC de riesgos laborales o ARL",
    "es_planilla": "si el documento es una planilla de seguridad social",
}


def _sin_tildes(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()


def enmascarar(texto: str, esperado: Expectativa | None = None) -> str:
    """Tapa cédula, nombre, correos, teléfonos y direcciones. No toca valores ni fechas."""
    t = texto
    if esperado:
        ced = re.escape(esperado.cedula)
        t = re.sub(rf"(?<!\d){ced}(?!\d)", "[CEDULA]", t)
        # con puntos de miles: 1.000.000.001
        conpuntos = f"{int(esperado.cedula):,}".replace(",", ".")
        t = t.replace(conpuntos, "[CEDULA]")
        for palabra in {p for p in esperado.nombre.split() if len(p) >= 3}:
            patron = "".join(f"{re.escape(c)}\\s?" for c in palabra)[:-3]  # tolera letras separadas
            t = re.sub(patron, "[NOMBRE]", t, flags=re.IGNORECASE)
            sin = _sin_tildes(palabra)
            if sin != palabra:
                t = re.sub(re.escape(sin), "[NOMBRE]", t, flags=re.IGNORECASE)
    t = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[CORREO]", t)
    t = re.sub(r"(?<![\d$.])3\d{9}(?!\d)", "[TELEFONO]", t)
    t = re.sub(r"(?im)^(.*direcci[oó]n)[^\n]*", r"\1 [DIRECCION]", t)
    # cualquier otro documento de identidad largo que siga a CC/CE
    t = re.sub(r"\b(CC|CE|C\.C\.)\s?\d{6,11}\b", r"\1 [DOCUMENTO]", t)
    return t


def documento_presente(texto: str, esperado: Expectativa | None) -> bool | None:
    """True si la cédula esperada aparece en el PDF; None si no hay a quién comparar."""
    if esperado is None:
        return None
    digitos = re.sub(r"[.\s]", "", texto)
    return esperado.cedula in digitos


def generar_paquete(texto: str, periodo: str, esperado: Expectativa | None = None,
                    caso: str = "") -> str:
    """Texto listo para copiar y pegar en Claude."""
    campos = "\n".join(f'  "{k}": {v}' for k, v in ESQUEMA.items())
    return f"""CASO {caso or 'sin código'} · Validador de seguridad social · periodo esperado {periodo}

Lee la planilla de seguridad social que está entre las marcas INICIO y FIN y transcribe
los campos. Reglas:
- Copia solo lo que aparece en el documento. Si un dato no está, escribe null. No lo deduzcas.
- Los datos personales están tapados con corchetes, como [CEDULA] o [NOMBRE]: es a propósito.
- No decidas si la planilla cumple: eso lo hace el sistema.
- Responde únicamente con un bloque ```json con estas claves:
{campos}

INICIO
{enmascarar(texto, esperado)}
FIN"""


def _extraer_json(respuesta: str) -> dict:
    bloque = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", respuesta, re.DOTALL)
    crudo = bloque.group(1) if bloque else respuesta[respuesta.find("{"): respuesta.rfind("}") + 1]
    if not crudo.strip():
        raise ValueError("No encontré el bloque de datos. Copia la respuesta completa de Claude, "
                         "incluido lo que está entre llaves { }.")
    try:
        return json.loads(crudo)
    except json.JSONDecodeError as e:
        raise ValueError("La respuesta no tiene un formato válido. Pídele a Claude: «Repite solo el "
                         f"bloque json, sin comentarios» (detalle: línea {e.lineno}).") from e


def _entero(v) -> int | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return int(round(v))
    digitos = re.sub(r"[^\d]", "", str(v))
    return int(digitos) if digitos else None


def leer_respuesta(respuesta: str, documento_coincide: bool | None = None,
                   esperado: Expectativa | None = None) -> tuple[Soporte | None, list[str]]:
    """Convierte lo que pegó la analista en un Soporte. Devuelve (soporte, problemas)."""
    try:
        datos = _extraer_json(respuesta)
    except ValueError as e:
        return None, [str(e)]
    problemas = []
    faltan = [k for k in OBLIGATORIOS if datos.get(k) is None]
    for k in faltan:
        problemas.append(f"Falta {AYUDA.get(k, k)}. Pídele a Claude: «Busca de nuevo {AYUDA.get(k, k)}».")
    periodo = datos.get("periodo")
    if periodo and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", str(periodo)):
        problemas.append(f"El periodo «{periodo}» no tiene el formato AAAA-MM, por ejemplo 2026-10.")
    fecha = None
    if datos.get("fecha_pago"):
        try:
            fecha = date.fromisoformat(str(datos["fecha_pago"]))
        except ValueError:
            problemas.append(f"La fecha de pago «{datos['fecha_pago']}» no tiene el formato AAAA-MM-DD.")
    tarifa = datos.get("tarifa_arl")
    try:
        tarifa = float(str(tarifa).replace(",", ".")) if tarifa not in (None, "") else None
    except ValueError:
        problemas.append(f"La tarifa de ARL «{tarifa}» no es un número.")
        tarifa = None
    if tarifa is not None and tarifa > 10:
        problemas.append(f"La tarifa de ARL {tarifa} parece estar en otra unidad; debe ser un porcentaje como 1.044.")
    if problemas:
        return None, problemas
    def booleano(v):
        return v if isinstance(v, bool) else str(v).strip().lower() in ("true", "si", "sí", "1")
    cedula = esperado.cedula if (documento_coincide and esperado) else (
        "DOCUMENTO-NO-COINCIDE" if documento_coincide is False else None)
    soporte = Soporte(
        es_planilla=booleano(datos["es_planilla"]), pagado=booleano(datos["pagado"]), cedula=cedula,
        periodo=str(periodo), tipo_planilla=(str(datos.get("tipo_planilla") or "").strip()[:1].upper() or None),
        tipo_empresa=datos.get("tipo_empresa"),
        tipo_cotizante=(str(datos["tipo_cotizante"]).zfill(2) if datos.get("tipo_cotizante") is not None else None),
        ibc_pension=_entero(datos["ibc_pension"]), ibc_salud=_entero(datos["ibc_salud"]),
        ibc_riesgos=_entero(datos["ibc_riesgos"]), tarifa_arl=tarifa,
        intereses_mora=_entero(datos.get("intereses_mora")), fecha_pago=fecha,
        operador=datos.get("operador"), numero_planilla=(str(datos["numero_planilla"]) if datos.get("numero_planilla") else None),
        origen_lectura="ia",
    )
    return soporte, []


def generar_paquete_plantilla(texto: str, soporte: Soporte, esperado: Expectativa | None = None) -> str:
    """Segundo paquete: pide a Claude una plantilla YAML para que este formato pase al carril 1."""
    confirmados = {k: v for k, v in soporte.model_dump(mode="json").items()
                   if k in ESQUEMA and v is not None}
    return f"""Plantilla nueva para el Validador de seguridad social.

Abajo está el texto de una planilla (datos personales tapados) y los valores que una
persona ya confirmó. Escribe una plantilla YAML con este formato exacto:

```yaml
operador: <nombre del operador>
estado: borrador
reconoce: [<2 o 3 textos fijos que solo aparecen en este formato>]
campos:
  <campo>: {{regex: '<expresión regular con UN grupo de captura>', tipo: <tipo>}}
```
Tipos permitidos: texto, pesos (número con puntos de miles), decimal (con coma o punto),
periodo_texto («octubre de 2026»), periodo_iso («2026-10»), fecha_dmy («04/11/2026»),
fecha_iso («2026-11-04»), existe (true si el regex encuentra algo).
Campos posibles: {', '.join(ESQUEMA)}.
Cada regex debe devolver exactamente el valor confirmado. No uses los corchetes [CEDULA] ni [NOMBRE].

Valores confirmados:
{json.dumps(confirmados, ensure_ascii=False, indent=1)}

INICIO
{enmascarar(texto, esperado)}
FIN"""
