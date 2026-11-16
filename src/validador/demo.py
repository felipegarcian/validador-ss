"""Demo de punta a punta con datos ficticios:  python -m validador.demo [carpeta]

Genera una liquidación y soportes ficticios con errores sembrados, los procesa
y escribe el Excel maestro. No usa datos reales ni se conecta a nada.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook

from .adaptadores import local
from .conciliacion import Mes
from .expectativas import cargar_liquidacion
from .salidas import correos, excel_maestro

PERIODO = "2026-10"
SOPORTE = """OPERADOR DEMO - Comprobante de pago de seguridad social
Planilla No. {planilla}
Cotizante: {nombre}
Identificación: {cedula}
Período: {periodo}
Total pagado: $ {valor}
Fecha de pago: {fecha}
Estado: {estado}
"""


def generar(raiz: Path, n: int = 12) -> None:
    (raiz / "01_Entrada").mkdir(parents=True, exist_ok=True)
    (raiz / "buzon").mkdir(parents=True, exist_ok=True)
    libro = Workbook()
    hoja = libro.active
    hoja.append(["cedula", "nombre", "devengado", "valor_esperado"])
    personas = []
    for i in range(n):
        esperado = 456000 + (i * 37 % 20) * 28500
        personas.append((str(1000000001 + i), f"Persona {i + 1:02d}", esperado * 6, esperado))
        hoja.append(list(personas[-1]))
    libro.save(raiz / "01_Entrada" / f"liquidacion_{PERIODO}.xlsx")

    # Errores sembrados: 3 pago menor, 4 pago mayor, 5 sin pagar, 6 otro mes, 7 dentro de tolerancia,
    # 8 formato desconocido, 9 cédula que no está, 10 y 11 no envían.
    for i, (cedula, nombre, _, esperado) in enumerate(personas[:10]):
        valor, periodo, estado, texto = esperado, PERIODO, "PAGADA", None
        if i == 3: valor = esperado - 71200
        if i == 4: valor = esperado + 57000
        if i == 5: estado = "PENDIENTE"
        if i == 6: periodo = "2026-09"
        if i == 7: valor = esperado - 600
        if i == 8: texto = "OTRO OPERADOR\nDocumento con un formato que ninguna plantilla conoce."
        if i == 9: cedula = "999999999"
        texto = texto or SOPORTE.format(planilla=7000000 + i, nombre=nombre, cedula=cedula, periodo=periodo,
                                        valor=f"{valor:,}".replace(",", "."), fecha="2026-11-04", estado=estado)
        (raiz / "buzon" / f"correo_{i + 1:02d}.txt").write_text(texto, encoding="utf-8")


def correr(raiz: Path) -> Mes:
    periodo, archivo = local.liquidacion(raiz)
    mes = Mes(periodo=periodo, expectativas=cargar_liquidacion(archivo))
    pagados: dict[str, int] = {}
    for _nombre, texto in local.soportes(raiz):
        from .lectura import plantillas
        soporte = plantillas.leer(texto)
        cedula, _ = mes.recibir_texto(texto, recibido=date(2026, 11, 4))
        if cedula and soporte and soporte.valor_pagado is not None:
            pagados[cedula] = soporte.valor_pagado
    mes.cerrar_corte(mes.fecha_limite)
    excel_maestro.escribir(mes, raiz / periodo / f"Control_SS_{periodo}.xlsx", pagados)
    return mes


def main() -> None:
    raiz = Path(sys.argv[1] if len(sys.argv) > 1 else "demo_salida")
    generar(raiz)
    mes = correr(raiz)
    print(f"Período {mes.periodo} · fecha límite {mes.fecha_limite}")
    for estado, cuenta in sorted(mes.resumen().items()):
        print(f"  {estado:<22} {cuenta}")
    borradores = sum(1 for c, r in mes.estados.items()
                     if correos.redactar(r, mes.expectativas[c], "octubre de 2026"))
    print(f"Borradores de correo listos: {borradores}")
    print(f"Excel maestro: {raiz / mes.periodo / f'Control_SS_{mes.periodo}.xlsx'}")


if __name__ == "__main__":
    main()
