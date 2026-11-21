"""Lectura, identificación, flujo del mes y salidas. Todo con datos ficticios."""
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from validador import calendario, demo
from validador.esquema import Estado, Expectativa
from validador.expectativas import cargar_base
from validador.lectura import plantillas
from validador.lectura.claves import candidatos_clave, cedulas_en_texto, identificar
from validador.salidas import correos

FIX = Path(__file__).parent / "fixtures"


def test_quinto_dia_habil_descuenta_festivos():
    # Noviembre de 2026: el lunes 2 es festivo, así que el quinto día hábil es el lunes 9.
    assert calendario.n_esimo_dia_habil(2026, 11, 5) == date(2026, 11, 9)
    assert calendario.mes_siguiente("2026-12") == (2027, 1)


def test_plantilla_suaporte():
    s = plantillas.leer(demo.texto_suaporte("Persona Ficticia", "1000000001", 4_422_191, mora=3000))
    assert s.operador == "SuAporte"
    assert (s.cedula, s.periodo, s.pagado, s.fecha_pago) == ("1000000001", "2026-10", True, date(2026, 11, 4))
    assert (s.tipo_empresa, s.tipo_planilla, s.tipo_cotizante, s.tarifa_arl) == ("INDEPENDIENTE", "I", "59", 1.044)
    assert (s.ibc_pension, s.ibc_salud, s.ibc_riesgos, s.ibc_pagado) == (4_422_191,) * 4
    assert s.intereses_mora == 3000


def test_plantilla_suaporte_sin_salud_ni_arl():
    s = plantillas.leer(demo.texto_suaporte("X", "1000000002", 1_750_905, tipo_cotizante="03",
                                            tarifa="0,000", ibc_salud=0, ibc_riesgos=0))
    assert s.tipo_cotizante == "03" and s.tarifa_arl == 0.0 and s.ibc_pagado == 0


def test_plantilla_suaporte_sin_pagar():
    assert plantillas.leer(demo.texto_suaporte("X", "1", 1, pagado=None)).pagado is False


def test_comprobante_enlace_no_trae_ibc():
    s = plantillas.leer((FIX / "enlace_comprobante_ficticio.txt").read_text(encoding="utf-8"))
    assert s.pagado is True and s.tipo_planilla == "E" and s.periodo == "2026-05" and s.ibc_pagado is None


def test_preplanilla_compensar_no_esta_pagada():
    s = plantillas.leer((FIX / "compensar_preplanilla_ficticia.txt").read_text(encoding="utf-8"))
    assert s.operador == "Compensar" and s.pagado is False and s.periodo == "2026-05"
    assert s.ibc_pagado == 1_750_905
    assert plantillas.leer("formato desconocido") is None


def test_identificar_por_nombre_del_remitente():
    exps = {c: Expectativa(cedula=c, nombre=n) for c, n in [
        ("1", "Marion Juliana Lozano Muñoz"), ("2", "Juliana Andrea Velez"),
        ("3", "Laura Elena Olarte"), ("4", "Lina Marcela Ochoa Vélez"), ("5", "Lina Marcela Londoño Soto")]}
    assert identificar("Juliana Lozano", exps) == "1"
    assert identificar("Laura Olrte", exps) == "3"           # error de tipeo
    assert identificar("Lina Ochoa", exps) == "4"
    assert identificar("Lina Marcela", exps) is None         # ambiguo: dos Lina Marcela
    assert identificar("", exps) is None


def test_orden_de_claves_para_pdf_con_contrasena():
    exps = {c: Expectativa(cedula=c, nombre=n) for c, n in
            [("111111", "Ana María Gómez"), ("222222", "Carlos Pérez"), ("333333", "Luisa Fernanda Ruiz")]}
    assert cedulas_en_texto("Adjunto planilla. CC 1.000.000.001") == ["1000000001"]
    orden = candidatos_clave("Mi cédula es 222.222", "Luisa Ruiz", exps)
    assert orden[0] == "222222" and orden[1] == "333333"
    assert candidatos_clave("", "", exps, cedula_conocida="333333")[0] == "333333"


def test_carga_la_base_con_el_formato_de_aza(tmp_path):
    archivo = demo.generar(tmp_path)
    exps = cargar_base(archivo)
    assert len(exps) == 14
    e = exps["1000000013"]
    assert e.especial and e.base_rtte == 1_050_000 and e.riesgo == "II"
    assert exps["1000000001"].correo == "prestador01@ejemplo.com"


def test_demo_de_punta_a_punta(tmp_path):
    demo.generar(tmp_path)
    mes = demo.correr(tmp_path)
    e = {int(c) - 1_000_000_000: r.estado for c, r in mes.estados.items()}
    assert e[1] == e[2] == Estado.OK
    assert e[3] == Estado.PAGO_DE_MAS
    assert e[4] == Estado.PENDIENTE_AJUSTE
    assert e[5] == Estado.OK                       # 600 pesos por debajo: tolerancia
    assert e[6] == Estado.PLANILLA_INCORRECTA      # no dice PAGADO
    assert e[7] == Estado.OTRO_PERIODO
    assert e[8] == Estado.REVISION_MANUAL          # tipo de cotizante 03
    assert e[9] == Estado.OK and mes.estados["1000000009"].aviso_riesgo
    assert e[10] == Estado.REVISION_MANUAL         # formato desconocido
    assert e[11] == Estado.OK and mes.estados["1000000011"].indicador == 0   # llegó tarde
    assert e[12] == Estado.NO_ENVIO
    assert e[13] == Estado.REVISION_MANUAL         # Especial
    assert e[14] == Estado.SIN_HONORARIOS
    ind = [v for v in mes.indicador().values() if v is not None]
    assert (sum(ind), len(ind)) == (5, 13)

    salida = tmp_path / "2026-10"
    libro = load_workbook(salida / "Control_SS_2026-10.xlsx")
    assert libro.sheetnames == ["Control", "Bitácora", "Correos", "Contabilidad"]
    assert libro["Control"].max_row == 15

    base = load_workbook(salida / "Base para SS 2026-10 (diligenciada).xlsx").worksheets[0]
    filas = {r[2]: r for r in base.iter_rows(min_row=3, values_only=True)}
    assert filas[1000000004][16] == "PENDIENTE AJUSTE" and filas[1000000004][13] is not None
    assert filas[1000000001][16] == "OK" and filas[1000000001][14] == 0

    ajuste = load_workbook(salida / "Formato Ajuste Seguridad social 2026-10.xlsx").active
    assert ajuste["B2"].value == "Prestador04 Ficticio Prueba"
    assert "riesgo II" in ajuste["A3"].value
    assert ajuste["B6"].value.startswith("=ROUND(")     # pensión con fórmula, en todos los bloques


def test_correos_con_causales_del_procedimiento(tmp_path):
    demo.generar(tmp_path)
    mes = demo.correr(tmp_path)
    por_causal = {b["causal"]: b for b in correos.borradores(mes)}
    assert set(por_causal) == {"7.1", "7.2", "7.3", "7.4", "7.5"}
    ajuste = por_causal["7.3"]
    assert ajuste["asunto"].startswith("Ajuste Seguridad Social Octubre")
    assert "Total ajuste $" in ajuste["cuerpo"] and ajuste["para"] == "prestador04@ejemplo.com"
    assert "09/11/2026" in por_causal["7.4"]["cuerpo"]
    # los estados que habilitan no generan correo
    assert correos.redactar(mes.estados["1000000001"], mes.expectativas["1000000001"], mes.periodo,
                            mes.fecha_limite) is None
