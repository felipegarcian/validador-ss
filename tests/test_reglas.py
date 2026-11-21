"""Reglas del procedimiento de AZA v3.0. Datos ficticios."""
from datetime import date

from validador.esquema import Estado, Expectativa, Reglas, Soporte
from validador.reglas import calcular_ajuste, evaluar

R = Reglas()
# Honorarios ficticios: 10.437.955 -> IBC requerido 4.175.182 (40 %, al peso)
EXP = Expectativa(cedula="1000000001", nombre="Persona Uno Prueba", base_rtte=10_437_955)
REQ = 4_175_182


def soporte(**cambios) -> Soporte:
    base = dict(cedula="1000000001", periodo="2026-10", pagado=True, tipo_empresa="INDEPENDIENTE",
                tipo_planilla="I", tipo_cotizante="59", tarifa_arl=1.044,
                ibc_pension=REQ, ibc_salud=REQ, ibc_riesgos=REQ, fecha_pago=date(2026, 11, 4))
    return Soporte(**{**base, **cambios})


def ev(s: Soporte, exp=EXP, **kw):
    return evaluar(s, exp, "2026-10", R, **kw)


def ibc(v: int) -> dict:
    return dict(ibc_pension=v, ibc_salud=v, ibc_riesgos=v)


def test_ibc_requerido_es_40_por_ciento_al_peso():
    assert R.ibc_requerido(EXP) == REQ
    # 11.055.477 × 40 % = 4.422.190,8 -> 4.422.191: pagar 4.422.191 es OK, no PAGO DE MÁS
    exp = Expectativa(cedula="2", nombre="X", base_rtte=11_055_477)
    assert R.ibc_requerido(exp) == 4_422_191
    assert evaluar(soporte(cedula="2", **ibc(4_422_191)), exp, "2026-10", R).estado == Estado.OK


def test_tolerancia_asimetrica():
    assert ev(soporte()).estado == Estado.OK
    assert ev(soporte(**ibc(REQ - 1000))).estado == Estado.OK
    assert ev(soporte(**ibc(REQ - 1001))).estado == Estado.PENDIENTE_AJUSTE
    assert ev(soporte(**ibc(REQ + 1))).estado == Estado.PAGO_DE_MAS   # cualquier peso por encima


def test_pendiente_ajuste_informa_la_diferencia_y_no_habilita():
    r = ev(soporte(**ibc(4_000_397)))
    assert r.estado == Estado.PENDIENTE_AJUSTE and r.diferencia == -174_785 and not r.habilita
    assert r.indicador == 0


def test_pago_de_mas_habilita_y_cuenta_uno_si_llego_a_tiempo():
    r = ev(soporte(**ibc(REQ + 250_000)), recibido=date(2026, 11, 4), fecha_limite=date(2026, 11, 9))
    assert r.estado == Estado.PAGO_DE_MAS and r.habilita and r.indicador == 1


def test_ibc_pagado_es_el_menor_de_los_tres():
    r = ev(soporte(ibc_pension=1_750_905, ibc_salud=0, ibc_riesgos=0, tipo_cotizante="59"))
    assert r.ibc_pagado == 0 and r.estado == Estado.PENDIENTE_AJUSTE
    assert any("IBC distintos" in o for o in r.observaciones)


def test_planilla_incorrecta():
    assert ev(soporte(pagado=False)).estado == Estado.PLANILLA_INCORRECTA
    assert ev(soporte(pagado=None)).estado == Estado.PLANILLA_INCORRECTA
    assert ev(soporte(cedula="999")).estado == Estado.PLANILLA_INCORRECTA
    assert ev(soporte(tipo_planilla="E")).estado == Estado.PLANILLA_INCORRECTA
    assert ev(soporte(es_planilla=False)).estado == Estado.PLANILLA_INCORRECTA


def test_otro_periodo():
    r = ev(soporte(periodo="2026-11"))
    assert r.estado == Estado.OTRO_PERIODO


def test_tipo_cotizante_distinto_va_a_revision():
    r = ev(soporte(tipo_cotizante="03"))
    assert r.estado == Estado.REVISION_MANUAL and r.codigo_error == "R-01"


def test_riesgo_arl_distinto_solo_avisa():
    r = ev(soporte(tarifa_arl=0.522))
    assert r.estado == Estado.OK and r.aviso_riesgo


def test_sin_honorarios_no_afecta_el_indicador():
    r = ev(soporte(), exp=Expectativa(cedula="1000000001", nombre="X", base_rtte=0))
    assert r.estado == Estado.SIN_HONORARIOS and r.indicador is None


def test_especial_usa_smmlv_y_va_a_revision():
    exp = Expectativa(cedula="1000000001", nombre="X", base_rtte=1_050_000, especial=True)
    assert R.ibc_requerido(exp) == R.smmlv
    r = ev(soporte(**ibc(R.smmlv)), exp=exp)
    assert r.estado == Estado.REVISION_MANUAL and r.codigo_error == "R-02" and r.diferencia == 0


def test_fuera_de_la_base_y_campos_faltantes():
    assert evaluar(soporte(), None, "2026-10", R).codigo_error == "I-01"
    assert ev(soporte(periodo=None)).codigo_error == "L-03"
    assert ev(soporte(ibc_salud=None)).codigo_error == "L-03"


def test_tarde_cuenta_cero_aunque_cumpla():
    r = ev(soporte(), recibido=date(2026, 11, 10), fecha_limite=date(2026, 11, 9))
    assert r.estado == Estado.OK and r.tardio and r.indicador == 0


def test_ajuste_suma_la_planilla_original():
    r = ev(soporte(**ibc(174_785)), ibc_previo=4_000_397)
    assert r.estado == Estado.AJUSTADO and r.ibc_pagado == REQ and r.indicador == 0


def test_observaciones_mora_y_pago_anticipado():
    r = ev(soporte(intereses_mora=3000, fecha_pago=date(2026, 10, 1)))
    assert any("mora" in o for o in r.observaciones)
    assert any("anticipado" in o for o in r.observaciones)


def test_calculo_del_ajuste_seccion_6():
    t = calcular_ajuste(REQ, 4_000_397, "II", R)
    assert t["IBC"]["ajuste"] == 174_785
    assert t["Pensión"]["ajuste"] == round(REQ * .16) - round(4_000_397 * .16)
    assert t["Total"]["ajuste"] == t["Pensión"]["ajuste"] + t["Salud"]["ajuste"] + t["ARL"]["ajuste"]
