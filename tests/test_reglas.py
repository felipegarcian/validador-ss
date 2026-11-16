from datetime import date

from validador.esquema import Estado, Expectativa, Reglas, Soporte
from validador.reglas import evaluar

EXP = Expectativa(cedula="1000000001", nombre="Persona Uno", valor_esperado=570000)
R = Reglas()


def soporte(**cambios) -> Soporte:
    base = dict(cedula="1000000001", periodo="2026-10", valor_pagado=570000, pagado=True)
    return Soporte(**{**base, **cambios})


def estado(s: Soporte, exp=EXP, **kw) -> Estado:
    return evaluar(s, exp, "2026-10", R, **kw).estado


def test_coincide():
    assert estado(soporte()) == Estado.CUMPLE


def test_tolerancia_de_mil_pesos_en_ambos_sentidos():
    assert estado(soporte(valor_pagado=569000)) == Estado.CUMPLE
    assert estado(soporte(valor_pagado=571000)) == Estado.CUMPLE
    assert estado(soporte(valor_pagado=568999)) == Estado.PAGO_MENOR
    assert estado(soporte(valor_pagado=571001)) == Estado.PAGO_MAYOR


def test_pago_menor_informa_la_diferencia():
    r = evaluar(soporte(valor_pagado=498800), EXP, "2026-10", R)
    assert r.estado == Estado.PAGO_MENOR and r.diferencia == -71200 and not r.habilita


def test_pago_mayor_habilita_y_se_conserva():
    r = evaluar(soporte(valor_pagado=627000), EXP, "2026-10", R)
    assert r.estado == Estado.PAGO_MAYOR and r.habilita


def test_planilla_sin_pagar():
    assert estado(soporte(pagado=False)) == Estado.SIN_PAGO


def test_otro_mes_y_otro_archivo():
    assert estado(soporte(periodo="2026-09")) == Estado.MES_O_ARCHIVO_ERRADO
    assert estado(soporte(es_soporte_pago=False)) == Estado.MES_O_ARCHIVO_ERRADO


def test_cedula_fuera_de_la_liquidacion_va_a_revision():
    r = evaluar(soporte(), None, "2026-10", R)
    assert r.estado == Estado.REVISION_MANUAL and r.codigo_error == "I-01"


def test_campos_faltantes_van_a_revision():
    assert estado(soporte(valor_pagado=None)) == Estado.REVISION_MANUAL


def test_tardio_se_marca_sin_cambiar_el_estado():
    r = evaluar(soporte(), EXP, "2026-10", R, recibido=date(2026, 11, 12), fecha_limite=date(2026, 11, 9))
    assert r.estado == Estado.CUMPLE and r.tardio
