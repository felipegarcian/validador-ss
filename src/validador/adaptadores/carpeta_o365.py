"""Adaptador «carpeta»: el motor trabaja sobre una biblioteca de SharePoint sincronizada.

Power Automate hace la parte de Office 365 (ver docs/AUTOMATIZACION_O365.md):
  - Flujo 1 guarda cada adjunto del buzón compartido en 01_Entrada/ con un .json al lado
    (remitente, asunto, fecha y hora de recepción).
  - Flujo 2 toma cada borrador de Correos/pendientes/, pide aprobación en Teams y, si se
    aprueba, lo envía desde el buzón compartido.
El motor no necesita permisos sobre el buzón ni registrar una aplicación para arrancar.

Cada ejecución es idempotente: reconstruye el mes desde todo lo recibido (68 planillas son
pocas), así que no hay base de datos ni estado escondido. Si una ejecución falla, la
siguiente deja todo igual.

  <raiz>/
    Base para SS*.xlsx                 la deja Contabilidad (la más reciente manda)
    01_Entrada/<id>.pdf + <id>.json     lo escribe Power Automate
    02_Procesados/                      el motor mueve aquí lo leído
    03_Por_revisar/<id>/                caso sin plantilla: paquete_claude.txt
                                        la analista pega respuesta_claude.txt
    Correos/pendientes/<id>-<causal>.json   borradores para el Flujo 2
    Correos/enviados/                   Power Automate los mueve aquí
    Salidas/                            Control, Base diligenciada, Formato de Ajuste,
                                        tablero_AAAA-MM.json (datos del tablero)
    salud.json                          última ejecución, conteos y errores
"""
from __future__ import annotations

import json
import shutil
import traceback
from datetime import date, datetime
from pathlib import Path

from ..conciliacion import Mes
from ..expectativas import cargar_base
from ..lectura import carril2_asistido as c2
from ..lectura import plantillas
from ..lectura.claves import abrir_con_clave, candidatos_clave, cedula_en_texto, identificar
from ..salidas import archivos_aza, correos, excel_maestro, tablero

CARPETAS = ["01_Entrada", "02_Procesados", "03_Por_revisar", "Correos/pendientes", "Correos/enviados", "Salidas"]


def preparar(raiz: str | Path) -> Path:
    raiz = Path(raiz)
    for c in CARPETAS:
        (raiz / c).mkdir(parents=True, exist_ok=True)
    return raiz


def _texto(archivo: Path, remitente: str, texto_correo: str, exps) -> tuple[str | None, str | None]:
    """Texto del adjunto. Devuelve (texto, error)."""
    if archivo.suffix.lower() == ".txt":
        return archivo.read_text(encoding="utf-8"), None
    abierto, _clave = abrir_con_clave(str(archivo), candidatos_clave(texto_correo, remitente, exps)[:5])
    if abierto is None:
        return None, "El PDF pide una contraseña que no es la cédula esperada."
    try:
        return "\n".join(p.extract_text() or "" for p in abierto.pages), None
    finally:
        abierto.close()


def _entradas(raiz: Path) -> list[tuple[Path, dict]]:
    pares = []
    for carpeta in ("02_Procesados", "01_Entrada"):
        for meta in (raiz / carpeta).glob("*.json"):
            adjunto = next((p for p in meta.parent.glob(meta.stem + ".*") if p.suffix != ".json"), None)
            if adjunto:
                pares.append((adjunto, json.loads(meta.read_text(encoding="utf-8"))))
    return sorted(pares, key=lambda x: x[1].get("recibido", ""))


def procesar(raiz: str | Path, periodo: str) -> dict:
    raiz = preparar(raiz)
    salud = {"ejecucion": datetime.now().isoformat(timespec="seconds"), "periodo": periodo,
             "procesados": 0, "nuevos": 0, "por_revisar": 0, "leidos_por_ia": 0, "errores": []}
    try:
        base = sorted(raiz.glob("Base para SS*.xlsx"), key=lambda p: p.stat().st_mtime)[-1]
    except IndexError:
        salud["errores"].append({"codigo": "I-02", "detalle": "No hay Base para SS en la carpeta."})
        _guardar(raiz / "salud.json", salud)
        return salud
    exps = cargar_base(base)
    mes = Mes(periodo=periodo, expectativas=exps)
    for adjunto, meta in _entradas(raiz):
        try:
            ident = adjunto.stem
            remitente = meta.get("remitente", "")
            recibido = date.fromisoformat(meta["recibido"][:10]) if meta.get("recibido") else None
            es_ajuste = "ajuste" in meta.get("asunto", "").lower()
            texto, error = _texto(adjunto, remitente, meta.get("cuerpo", ""), exps)
            caso = raiz / "03_Por_revisar" / ident
            if texto is None:
                salud["por_revisar"] += 1
                caso.mkdir(exist_ok=True)
                (caso / "motivo.txt").write_text(error + " Pide la clave al prestador.", encoding="utf-8")
            elif plantillas.leer(texto) is not None:
                mes.recibir_texto(texto, recibido, remitente, es_ajuste)
            else:
                cedula = cedula_en_texto(texto, exps) or identificar(remitente, exps)
                esperado = exps.get(cedula or "")
                respuesta = caso / "respuesta_claude.txt"
                if respuesta.exists():
                    soporte, problemas = c2.leer_respuesta(respuesta.read_text(encoding="utf-8"),
                                                           c2.documento_presente(texto, esperado), esperado)
                    if soporte:
                        mes.recibir(soporte, recibido, remitente, es_ajuste)
                        salud["leidos_por_ia"] += 1
                        (caso / "problemas.txt").unlink(missing_ok=True)
                    else:
                        (caso / "problemas.txt").write_text("\n".join(problemas), encoding="utf-8")
                        salud["por_revisar"] += 1
                else:
                    caso.mkdir(exist_ok=True)
                    (caso / "paquete_claude.txt").write_text(
                        c2.generar_paquete(texto, periodo, esperado, ident), encoding="utf-8")
                    mes.recibir_texto(texto, recibido, remitente, es_ajuste)  # deja REVISIÓN MANUAL L-01
                    salud["por_revisar"] += 1
            salud["procesados"] += 1
            if adjunto.parent.name == "01_Entrada":
                for p in (adjunto, adjunto.with_suffix(".json")):
                    shutil.move(str(p), raiz / "02_Procesados" / p.name)
                salud["nuevos"] += 1
        except Exception as e:  # un archivo malo no detiene el mes
            salud["errores"].append({"codigo": "L-02", "archivo": adjunto.name, "detalle": str(e),
                                     "traza": traceback.format_exc(limit=2)})
    _salidas(raiz, base, mes, salud)
    _guardar(raiz / "salud.json", salud)
    return salud


def _salidas(raiz: Path, base: Path, mes: Mes, salud: dict) -> None:
    sal = raiz / "Salidas"
    excel_maestro.escribir(mes, sal / f"Control_SS_{mes.periodo}.xlsx")
    archivos_aza.escribir_base(base, mes, sal / f"{base.stem} (diligenciada).xlsx")
    archivos_aza.escribir_formato_ajuste(mes, sal / f"Formato Ajuste Seguridad social {mes.periodo}.xlsx")
    tablero.escribir(mes, sal / f"tablero_{mes.periodo}.json")  # docs/TABLERO.md
    ya = {p.stem for p in (raiz / "Correos").rglob("*.json")}
    for b in correos.borradores(mes):
        nombre = f"{b['cedula']}-{b['causal'].replace('.', '_')}-{mes.periodo}"
        if nombre not in ya:
            _guardar(raiz / "Correos" / "pendientes" / f"{nombre}.json", b)
    salud["estados"] = mes.resumen()
    salud["habilitados"] = sum(1 for r in mes.estados.values() if r.habilita)


def _guardar(ruta: Path, datos: dict) -> None:
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Procesa la carpeta sincronizada de Seguridad Social.")
    ap.add_argument("raiz")
    ap.add_argument("--periodo", required=True, help="AAAA-MM del periodo de cotización")
    a = ap.parse_args()
    s = procesar(a.raiz, a.periodo)
    print(json.dumps({k: v for k, v in s.items() if k != "errores"}, ensure_ascii=False, default=str))
    for e in s["errores"]:
        print(f"[{e['codigo']}] {e.get('archivo', '')} {e['detalle']}")


if __name__ == "__main__":
    main()
