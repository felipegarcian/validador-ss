from datetime import date

from openpyxl import load_workbook

from validador import calendario, demo
from validador.esquema import Estado, Expectativa
from validador.lectura import plantillas
from validador.lectura.claves import candidatos_clave, cedulas_en_texto
from validador.salidas import correos


def test_quinto_dia_habil_descuenta_festivos():
    # Noviembre de 2026: el lunes 2 es festivo, así que el quinto día hábil es el lunes 9.
    assert calendario.n_esimo_dia_habil(2026, 11, 5) == date(2026, 11, 9)
    assert calendario.mes_siguiente("2026-12") == (2027, 1)


def test_plantilla_demo_lee_los_campos():
    texto = demo.SOPORTE.format(planilla=7000001, nombre="Persona 01", cedula="1.000.000.001",
                                periodo="2026-10", valor="570.000", fecha="2026-11-04", estado="PAGADA")
    s = plantillas.leer(texto)
    assert (s.cedula, s.periodo, s.valor_pagado, s.pagado) == ("1000000001", "2026-10", 570000, True)
    assert plantillas.leer("formato desconocido") is None


def test_orden_de_claves_para_pdf_con_contrasena():
    exps = {c: Expectativa(cedula=c, nombre=n, valor_esperado=1) for c, n in
            [("111111", "Ana María Gómez"), ("222222", "Carlos Pérez"), ("333333", "Luisa Fernanda Ruiz")]}
    assert cedulas_en_texto("Adjunto planilla. CC 1.000.000.001") == ["1000000001"]
    # 1) cédula escrita en el correo; 2) el resto por parecido con el nombre del remitente
    orden = candidatos_clave("Mi cédula es 222.222", "Luisa Ruiz", exps)
    assert orden[0] == "222222" and orden[1] == "333333"
    # la cédula ya conocida del remitente va antes que todo
    assert candidatos_clave("", "", exps, cedula_conocida="333333")[0] == "333333"


def test_demo_de_punta_a_punta(tmp_path):
    demo.generar(tmp_path)
    mes = demo.correr(tmp_path)
    e = {c: r.estado for c, r in mes.estados.items()}
    assert e["1000000004"] == Estado.PAGO_MENOR
    assert e["1000000005"] == Estado.PAGO_MAYOR
    assert e["1000000006"] == Estado.SIN_PAGO
    assert e["1000000007"] == Estado.MES_O_ARCHIVO_ERRADO
    assert e["1000000008"] == Estado.CUMPLE          # dentro de la tolerancia
    assert e["1000000009"] == Estado.NO_ENTREGO      # su correo traía un formato desconocido
    assert e["1000000011"] == Estado.NO_ENTREGO and e["1000000012"] == Estado.NO_ENTREGO
    assert mes.resumen()[Estado.CUMPLE.value] == 4
    # formato desconocido y cédula ajena quedaron en la bitácora como revisión manual
    assert sum(1 for b in mes.bitacora if b["evento"] in ("LECTURA", Estado.REVISION_MANUAL.value)) == 2

    libro = load_workbook(tmp_path / "2026-10" / "Control_SS_2026-10.xlsx")
    assert libro.sheetnames == ["Control", "Bitácora", "Contabilidad"]
    assert libro["Control"].max_row == 13            # encabezado + 12 prestadores
    assert libro["Contabilidad"].max_row == 6        # encabezado + 4 cumplen + 1 pago mayor


def test_correo_de_pago_menor_lleva_las_cifras_de_la_validacion(tmp_path):
    demo.generar(tmp_path)
    mes = demo.correr(tmp_path)
    exp, r = mes.expectativas["1000000004"], mes.estados["1000000004"]
    asunto, cuerpo = correos.redactar(r, exp, "octubre de 2026")
    assert "$ 71.200" in cuerpo and exp.nombre in cuerpo
    # los estados que habilitan no generan correo
    assert correos.redactar(mes.estados["1000000001"], mes.expectativas["1000000001"], "octubre de 2026") is None
