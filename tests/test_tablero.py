"""Contrato de datos del tablero y verificador de cifras. Todo con datos ficticios."""
import json
from datetime import date, datetime

from openpyxl import load_workbook

from validador import calendario, demo
from validador.salidas import correos, tablero, verificador

FIJO = datetime(2026, 11, 10, 8, 0, 0)


def _mes(tmp_path):
    demo.generar(tmp_path)
    return demo.correr(tmp_path)


def test_la_demo_escribe_el_tablero(tmp_path):
    _mes(tmp_path)
    datos = json.loads((tmp_path / "2026-10" / "tablero_2026-10.json").read_text(encoding="utf-8"))
    assert datos["version"] == tablero.VERSION and datos["periodo"] == "2026-10"
    assert datos["fecha_limite"] == "2026-11-09"
    assert datos["resumen"] == {"texto": None, "origen": None}


def test_indicadores_cuadran_con_el_excel_maestro(tmp_path):
    mes = _mes(tmp_path)
    datos = tablero.construir(mes, generado=FIJO)
    ind = datos["indicadores"]
    # Oportunidad: 5 de 13; SIN HONORARIOS no cuenta.
    assert (ind["oportunidad"]["cumplen"], ind["oportunidad"]["total"]) == (5, 13)
    assert ind["oportunidad"]["valor"] == round(5 / 13, 4)

    control = load_workbook(tmp_path / "2026-10" / "Control_SS_2026-10.xlsx")["Control"]
    filas = list(control.iter_rows(min_row=2, values_only=True))
    estados_excel: dict[str, int] = {}
    for f in filas:
        estados_excel[f[16]] = estados_excel.get(f[16], 0) + 1
    assert ind["por_estado"] == dict(sorted(estados_excel.items()))
    assert len(datos["casos"]) == len(filas)
    habilitan_excel = sum(1 for f in filas if f[18] == "sí")
    assert ind["habilitados"]["cumplen"] == habilitan_excel
    assert ind["habilitados"]["total"] == 13
    assert ind["por_codigo"].get("L-01") == 1
    assert ind["por_origen"] == {"plantilla": 11}
    assert ind["dias_habiles_al_corte"] == 0       # el 10 de noviembre ya pasó el corte


def test_casos_traen_las_cifras_del_resultado(tmp_path):
    mes = _mes(tmp_path)
    casos = {c["cedula"]: c for c in tablero.construir(mes, generado=FIJO)["casos"]}
    c = casos["1000000004"]
    r = mes.estados["1000000004"]
    assert c["estado"] == "PENDIENTE AJUSTE" and c["habilita"] is False
    assert (c["ibc_requerido"], c["ibc_pagado"], c["diferencia"]) == (r.ibc_requerido, r.ibc_pagado, r.diferencia)
    assert c["explicacion"] is None and c["explicacion_origen"] is None
    assert casos["1000000014"]["indicador"] is None    # sin honorarios
    assert casos["1000000011"]["tardio"] is True


def test_correos_enlazados_a_su_caso_con_sus_cifras(tmp_path):
    mes = _mes(tmp_path)
    datos = tablero.construir(mes, generado=FIJO)
    ids = {c["id"]: c for c in datos["casos"]}
    assert len(datos["correos"]) == len(correos.borradores(mes))
    for m in datos["correos"]:
        assert m["caso"] in ids
        assert verificador.conserva_cifras(m["asunto"] + "\n" + m["cuerpo"], m["cifras"])
    ajuste = next(m for m in datos["correos"] if m["causal"] == "7.3")
    assert ids[ajuste["caso"]]["cedula"] == "1000000004"
    assert any(c.startswith("$") for c in ajuste["cifras"])


def test_sin_identificar_aparece_y_no_habilita():
    mes = _mes_sin_identificar()
    datos = tablero.construir(mes, generado=FIJO)
    caso = next(c for c in datos["casos"] if c["id"] == "s-01")
    assert caso["cedula"] is None and caso["habilita"] is False and caso["codigo_error"] == "L-04"
    assert caso["nombre"] == "SIN IDENTIFICAR: Persona Desconocida"
    pedido = next(m for m in datos["correos"] if m["causal"] == "4.3")
    assert pedido["caso"] == "s-01" and pedido["para"] == "otra@ejemplo.com"
    assert datos["indicadores"]["sin_identificar"] == 1


def _mes_sin_identificar():
    from validador.conciliacion import Mes
    from validador.esquema import Expectativa
    mes = Mes(periodo="2026-10", expectativas={
        "1000000001": Expectativa(cedula="1000000001", nombre="Ana María Gómez Ficticia", base_rtte=5_000_000)})
    mes.recibir_sin_abrir(remitente="Persona Desconocida", correo_remitente="otra@ejemplo.com", archivo="x.pdf")
    return mes


def test_el_json_es_estable_entre_ejecuciones(tmp_path):
    mes = _mes(tmp_path)
    a = tablero.escribir(mes, tmp_path / "a.json", generado=FIJO).read_text(encoding="utf-8")
    b = tablero.escribir(mes, tmp_path / "b.json", generado=FIJO).read_text(encoding="utf-8")
    assert a == b
    json.loads(a)


def test_dias_habiles_al_corte():
    # Del miércoles 4 al lunes 9 de noviembre de 2026: jueves 5, viernes 6 y lunes 9.
    assert calendario.dias_habiles_hasta(date(2026, 11, 4), date(2026, 11, 9)) == 3
    assert calendario.dias_habiles_hasta(date(2026, 11, 10), date(2026, 11, 9)) == 0


# --- Verificador de cifras ---

BORRADOR = ("Hola Ana: según tus honorarios de octubre 2026 por $5.000.000, el IBC requerido es $2.000.000. "
            "Tu planilla reporta $1.825.215. Envía la planilla a más tardar el 09/11/2026.")


def test_verificador_reconoce_pesos_porcentajes_y_fechas():
    assert verificador.cifras(BORRADOR) == {"$5.000.000", "$2.000.000", "$1.825.215", "09/11/2026"}
    assert verificador.cifras("tarifa 1,044 % y $ 1.600.000.") == {"1,044%", "$1.600.000"}
    assert verificador.cifras("diferencia $-174.785") == {"$-174.785"}


def test_correo_editado_sin_tocar_cifras_pasa():
    originales = verificador.cifras(BORRADOR)
    editado = BORRADOR.replace("Hola Ana:", "Buen día, Ana.").replace("Envía", "Por favor envía")
    assert verificador.conserva_cifras(editado, originales)


def test_correo_con_cifra_cambiada_o_borrada_no_pasa():
    originales = verificador.cifras(BORRADOR)
    assert not verificador.conserva_cifras(BORRADOR.replace("$2.000.000", "$2.100.000"), originales)
    assert not verificador.conserva_cifras(BORRADOR.replace(" a más tardar el 09/11/2026", ""), originales)


def test_texto_de_ia_con_cifra_inventada_se_detecta():
    permitidas = {"$2.000.000", "$1.825.215", "7", "12"}
    assert verificador.sin_cifras_nuevas("7 de 12 prestadores están habilitados.", permitidas)
    malo = "7 de 12 habilitados; faltan $174.785 y 3 casos."
    assert not verificador.sin_cifras_nuevas(malo, permitidas)
    assert verificador.cifras_nuevas(malo, permitidas) == {"$174.785", "3"}
