"""Carril 2 asistido, plantillas YAML y adaptador de carpeta. Datos ficticios."""
import json
from pathlib import Path

import pytest

from validador import demo
from validador.adaptadores import carpeta_o365
from validador.esquema import Estado, Expectativa, Reglas
from validador.lectura import carril2_asistido as c2
from validador.lectura.plantillas import cargar_plantillas_yaml, plantilla_desde_yaml
from validador.reglas import evaluar

EXP = Expectativa(cedula="1000000001", nombre="Ana María Gómez Prueba", base_rtte=6_000_000)
TEXTO_NUEVO = """OPERADOR NUEVO S.A.S · Planilla Integrada de Aportes
Aportante: ANA MARIA GOMEZ PRUEBA  Documento CC 1000000001
Dirección: Calle Falsa 123  Correo ana@ejemplo.com  Tel 3001234567
Periodo pensión: 2026-10   Estado: PAGADA el 04/11/2026
Tipo planilla I · Cotizante 59
IBC Pensión 2.400.000  IBC Salud 2.400.000  IBC ARL 2.400.000  Tarifa ARL 1,044
Total pagado $ 664.700
"""
RESPUESTA = """Aquí está:
```json
{"es_planilla": true, "pagado": true, "periodo": "2026-10", "tipo_planilla": "I",
 "tipo_empresa": null, "tipo_cotizante": "59", "ibc_pension": 2400000, "ibc_salud": "2.400.000",
 "ibc_riesgos": 2400000, "tarifa_arl": "1,044", "intereses_mora": 0, "fecha_pago": "2026-11-04",
 "operador": "Operador Nuevo", "numero_planilla": null}
```"""


def test_el_paquete_no_lleva_datos_personales_pero_si_los_valores():
    p = c2.generar_paquete(TEXTO_NUEVO, "2026-10", EXP, "C-001")
    for dato in ["1000000001", "ANA", "GOMEZ", "ana@ejemplo.com", "3001234567", "Calle Falsa"]:
        assert dato not in p
    assert "2.400.000" in p and "2026-10" in p and "[CEDULA]" in p and "```json" in p


def test_documento_se_verifica_localmente():
    assert c2.documento_presente(TEXTO_NUEVO, EXP) is True
    assert c2.documento_presente(TEXTO_NUEVO.replace("1000000001", "999"), EXP) is False


def test_respuesta_valida_entra_a_las_mismas_reglas():
    s, problemas = c2.leer_respuesta(RESPUESTA, True, EXP)
    assert problemas == [] and s.origen_lectura == "ia" and s.cedula == EXP.cedula
    assert s.ibc_salud == 2_400_000 and s.tarifa_arl == 1.044
    assert evaluar(s, EXP, "2026-10", Reglas()).estado == Estado.OK


def test_documento_que_no_coincide_termina_en_planilla_incorrecta():
    s, _ = c2.leer_respuesta(RESPUESTA, False, EXP)
    assert evaluar(s, EXP, "2026-10", Reglas()).estado == Estado.PLANILLA_INCORRECTA


def test_problemas_en_lenguaje_simple():
    _, p = c2.leer_respuesta(RESPUESTA.replace('"ibc_salud": "2.400.000"', '"ibc_salud": null'), True, EXP)
    assert any("IBC de salud" in x and "Pídele a Claude" in x for x in p)
    _, p = c2.leer_respuesta("no copié nada", True, EXP)
    assert "bloque de datos" in p[0]
    _, p = c2.leer_respuesta("```json\n{\"periodo\": octubre}\n```", True, EXP)
    assert "formato válido" in p[0]


PLANTILLA = {
    "operador": "Operador Nuevo", "estado": "activa",
    "reconoce": ["OPERADOR NUEVO S.A.S", "Planilla Integrada de Aportes"],
    "campos": {
        "periodo": {"regex": r"Periodo pensi[oó]n:\s*(\d{4}-\d{2})", "tipo": "periodo_iso"},
        "pagado": {"regex": r"Estado:\s*PAGADA", "tipo": "existe"},
        "fecha_pago": {"regex": r"PAGADA el (\d{2}/\d{2}/\d{4})", "tipo": "fecha_dmy"},
        "cedula": {"regex": r"Documento CC (\d+)", "tipo": "texto"},
        "tipo_planilla": {"regex": r"Tipo planilla (\w)", "tipo": "texto"},
        "tipo_cotizante": {"regex": r"Cotizante (\d{2})", "tipo": "texto"},
        "ibc_pension": {"regex": r"IBC Pensi[oó]n ([\d.]+)", "tipo": "pesos"},
        "ibc_salud": {"regex": r"IBC Salud ([\d.]+)", "tipo": "pesos"},
        "ibc_riesgos": {"regex": r"IBC ARL ([\d.]+)", "tipo": "pesos"},
        "tarifa_arl": {"regex": r"Tarifa ARL ([\d,]+)", "tipo": "decimal"},
    },
}


def test_plantilla_yaml_lee_el_formato_nuevo(tmp_path):
    import yaml
    (tmp_path / "nuevo.yaml").write_text(yaml.safe_dump(PLANTILLA, allow_unicode=True), encoding="utf-8")
    borrador = dict(PLANTILLA, estado="borrador")
    (tmp_path / "otro.yaml").write_text(yaml.safe_dump(borrador, allow_unicode=True), encoding="utf-8")
    activas = cargar_plantillas_yaml(str(tmp_path))
    assert len(activas) == 1 and len(cargar_plantillas_yaml(str(tmp_path), incluir_borradores=True)) == 2
    s = activas[0].extraer(TEXTO_NUEVO)
    assert (s.periodo, s.pagado, s.ibc_pagado, s.tarifa_arl, s.cedula) == ("2026-10", True, 2_400_000, 1.044, "1000000001")
    # misma respuesta que Claude: la plantilla puede aprobarse
    ia, _ = c2.leer_respuesta(RESPUESTA, True, EXP)
    assert (s.periodo, s.ibc_pagado, s.tarifa_arl, s.fecha_pago) == (ia.periodo, ia.ibc_pagado, ia.tarifa_arl, ia.fecha_pago)


def test_plantilla_mal_escrita_se_rechaza_con_motivo():
    mala = dict(PLANTILLA, campos={"periodo": {"regex": r"(\d{4})-(\d{2})", "tipo": "periodo_iso"}})
    with pytest.raises(ValueError, match="un grupo"):
        plantilla_desde_yaml(mala)
    with pytest.raises(ValueError, match="desconocido"):
        plantilla_desde_yaml(dict(PLANTILLA, campos={"clave_secreta": {"regex": "(x)"}}))


def _correo(entrada: Path, ident: str, texto: str, remitente: str, recibido="2026-11-04T09:00:00",
            asunto="Seguridad Social octubre"):
    (entrada / f"{ident}.txt").write_text(texto, encoding="utf-8")
    (entrada / f"{ident}.json").write_text(json.dumps({"remitente": remitente, "recibido": recibido,
                                                       "asunto": asunto}), encoding="utf-8")


def test_carpeta_de_punta_a_punta_con_carril_2(tmp_path):
    demo.generar(tmp_path)
    raiz = carpeta_o365.preparar(tmp_path)
    exps = {e.cedula: e for e in __import__("validador.expectativas", fromlist=["x"]).cargar_base(
        tmp_path / "Base para SS 2026-10.xlsx").values()}
    r = Reglas()
    p1, p2 = exps["1000000001"], exps["1000000002"]
    _correo(raiz / "01_Entrada", "a1", demo.texto_suaporte(p1.nombre, p1.cedula, r.ibc_requerido(p1)), p1.nombre)
    ibc2 = r.ibc_requerido(p2)
    texto2 = TEXTO_NUEVO.replace("1000000001", p2.cedula).replace("2.400.000", f"{ibc2:,}".replace(",", "."))
    _correo(raiz / "01_Entrada", "a2", texto2, p2.nombre)

    s = carpeta_o365.procesar(raiz, "2026-10")
    assert s["nuevos"] == 2 and s["por_revisar"] == 1 and not s["errores"]
    paquete = (raiz / "03_Por_revisar" / "a2" / "paquete_claude.txt").read_text(encoding="utf-8")
    assert p2.cedula not in paquete and "```json" in paquete
    assert s["estados"]["OK"] == 1 and s["estados"]["REVISIÓN MANUAL"] == 1
    assert not list((raiz / "01_Entrada").iterdir())

    # La analista pega la respuesta de Claude y el siguiente ciclo la toma
    resp = RESPUESTA.replace("2400000", str(ibc2)).replace('"2.400.000"', str(ibc2))
    (raiz / "03_Por_revisar" / "a2" / "respuesta_claude.txt").write_text(resp, encoding="utf-8")
    s = carpeta_o365.procesar(raiz, "2026-10")
    assert s["leidos_por_ia"] == 1 and s["estados"]["OK"] == 2 and s["nuevos"] == 0
    assert (raiz / "Salidas" / "Control_SS_2026-10.xlsx").exists()
    salud = json.loads((raiz / "salud.json").read_text(encoding="utf-8"))
    assert salud["habilitados"] == 2
    datos = json.loads((raiz / "Salidas" / "tablero_2026-10.json").read_text(encoding="utf-8"))
    assert datos["indicadores"]["habilitados"]["cumplen"] == 2
    assert datos["indicadores"]["por_origen"].get("ia") == 1   # el caso que leyó Claude se ve en el tablero

    # Idempotente: otra corrida no duplica borradores
    antes = len(list((raiz / "Correos" / "pendientes").glob("*.json")))
    carpeta_o365.procesar(raiz, "2026-10")
    assert len(list((raiz / "Correos" / "pendientes").glob("*.json"))) == antes
