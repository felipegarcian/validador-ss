"""Demo de punta a punta con datos ficticios:  python -m validador.demo [carpeta]

Genera una Base con el formato real de AZA y planillas ficticias con la estructura de
SuAporte (el operador más común en los insumos), con casos sembrados de cada estado.
Ningún nombre, cédula ni valor corresponde a una persona real.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook

from .conciliacion import Mes
from .expectativas import cargar_base
from .salidas import archivos_aza, correos, excel_maestro, tablero

PERIODO = "2026-10"
MESES_TXT = {"2026-09": "septiembre de 2026", "2026-10": "octubre de 2026", "2026-11": "noviembre de 2026"}


def pesos(v: int) -> str:
    return "$ " + f"{v:,}".replace(",", ".")


def texto_suaporte(nombre: str, cedula: str, ibc: int, periodo: str = PERIODO, pagado: str | None = "04/11/2026",
                   tipo_cotizante: str = "59", tarifa: str = "1,044", ibc_salud: int | None = None,
                   ibc_riesgos: int | None = None, mora: int = 0, planilla: str = "70000001") -> str:
    """Texto con la misma estructura que extrae pdfplumber de una planilla SuAporte."""
    ibc_s = ibc if ibc_salud is None else ibc_salud
    ibc_r = ibc if ibc_riesgos is None else ibc_riesgos
    ap = [round(ibc * 0.16, -2), round(ibc_s * 0.125, -2), round(ibc_r * float(tarifa.replace(",", ".")) / 100, -2)]
    total = int(sum(ap))
    linea_pago = f"PAGADO {pagado}" if pagado else "PENDIENTE DE PAGO"
    return f"""|
AUTOLIQUIDACION
CONSOLIDADA
Fecha creación reporte: 2026-11-04, 08:00:00 AM Numéro Planilla: {planilla}
Periodo Cotización: {MESES_TXT[periodo]} Periodo Servicio: {MESES_TXT[periodo]}
{linea_pago}
I. DATOS DEL APORTANTE
Razón Social {nombre.upper()}
Documento CC{cedula} Dirección CALLE FICTICIA 1 # 2 - 3
Tipo de Empresa INDEPENDIENTE Teléfono 0
SuAporte
Tipo Planilla: I: PLANILLA INDEPENDIENTES
II. DETALLE DEL APORTANTE
CC {cedula} N O M B R E R E V U E L T O {tipo_cotizante} 00 030303030(230301) FONDO {pesos(ibc)} {pesos(int(ap[0]))}(EPS000) EPS {pesos(ibc_s)} {pesos(int(ap[1]))} {tarifa} {pesos(ibc_r)} {pesos(int(ap[2]))}(NIN-CC) NINGUNA CCF $ 0 $ 0 $ 0 $ 0 $ 0 $ 0 {pesos(total)}
III.TOTALES
IBC Pensión IBC Salud IBC Riesgos IBC Cajas Aportes Pensión Aportes Salud Aportes Riesgos TOTAL FINAL
{pesos(ibc)} {pesos(ibc_s)} {pesos(ibc_r)} $ 0 {pesos(int(ap[0]))} {pesos(int(ap[1]))} {pesos(int(ap[2]))} $ 0 $ 0 $ 0 $ 0 $ 0 $ 0 $ 0 {pesos(total)} {pesos(mora)} {pesos(total + mora)}
Página 1 de 1
"""


def generar(raiz: Path, n: int = 14) -> Path:
    """Base ficticia con el formato de AZA y un buzón de correos con casos sembrados."""
    (raiz / "buzon").mkdir(parents=True, exist_ok=True)
    libro = Workbook()
    hoja = libro.active
    hoja.title = "OCTUBRE"
    hoja["B1"], hoja["N1"] = "Lo que trae la base inicialmente", "Información que se diligencia despues del analisis"
    hoja.append([None, "ASESOR", "CÉDULA", "CORREO", "tipo de riesgo", "Especial", "BASE RTTE OCTUBRE 2026",
                 "IBC 40%", "PENSION ", "SALUD", "ARL RIESGO II", "TOTAL PAGO SEGURIDAD SOCIAL ", None,
                 "IBC PAGADO", "NUEVO  PENSION ", "NUEVO SALUD", "ESTADO"])
    personas = []
    for i in range(n):
        base = 3_000_000 + (i * 37 % 20) * 350_000
        especial = "Especial" if i == 12 else None
        if i == 12:
            base = 1_050_000
        if i == 13:
            base = 0  # sin honorarios
        cedula = str(1_000_000_001 + i)
        nombre = f"Prestador{i + 1:02d} Ficticio Prueba"
        personas.append((cedula, nombre, base))
        ibc = base * 0.4
        hoja.append([None, nombre, int(cedula), f"prestador{i + 1:02d}@ejemplo.com", "II", especial, base, ibc,
                     ibc * 0.16, ibc * 0.125, ibc * 0.01044, ibc * 0.29544])
    archivo = raiz / f"Base para SS {PERIODO}.xlsx"
    libro.save(archivo)

    # Casos: 0-1 OK, 2 pago de más, 3 pendiente ajuste, 4 dentro de tolerancia (-600), 5 sin pagar,
    # 6 otro periodo, 7 tipo cotizante 03 sin salud ni ARL, 8 riesgo I pagado (aviso 7.5),
    # 9 formato desconocido, 10 tarde, 11 no envía, 12 especial, 13 sin honorarios.
    correos_demo = []
    for i, (cedula, nombre, base) in enumerate(personas[:13]):
        req = round(base * 0.4)
        kw: dict = {}
        cuando = "2026-11-04"
        if i == 2: kw["ibc"] = req + 250_000
        if i == 3: kw["ibc"] = req - 174_785
        if i == 4: kw["ibc"] = req - 600
        if i == 5: kw["pagado"] = None
        if i == 6: kw["periodo"] = "2026-11"
        if i == 7: kw.update(tipo_cotizante="03", tarifa="0,000", ibc_salud=0, ibc_riesgos=0)
        if i == 8: kw["tarifa"] = "0,522"
        if i == 10: cuando = "2026-11-12"
        if i == 11: continue
        if i == 12: kw["ibc"] = 1_750_905
        kw.setdefault("ibc", req)
        texto = (texto_suaporte(nombre, cedula, planilla=str(70000001 + i), **kw) if i != 9
                 else "OTRO OPERADOR\nDocumento con un formato que ninguna plantilla conoce.")
        remitente = " ".join(nombre.split()[:2])
        correos_demo.append({"archivo": f"correo_{i + 1:02d}.txt", "remitente": remitente, "recibido": cuando})
        (raiz / "buzon" / f"correo_{i + 1:02d}.txt").write_text(texto, encoding="utf-8")
    (raiz / "buzon" / "correos.json").write_text(json.dumps(correos_demo, indent=1), encoding="utf-8")
    return archivo


def correr(raiz: Path) -> Mes:
    archivo = sorted(raiz.glob("Base para SS *.xlsx"))[-1]
    periodo = archivo.stem.split()[-1]
    mes = Mes(periodo=periodo, expectativas=cargar_base(archivo))
    for correo in json.loads((raiz / "buzon" / "correos.json").read_text(encoding="utf-8")):
        texto = (raiz / "buzon" / correo["archivo"]).read_text(encoding="utf-8")
        mes.recibir_texto(texto, recibido=date.fromisoformat(correo["recibido"]), remitente=correo["remitente"])
    mes.cerrar_corte(mes.fecha_limite)
    salida = raiz / periodo
    excel_maestro.escribir(mes, salida / f"Control_SS_{periodo}.xlsx")
    archivos_aza.escribir_base(archivo, mes, salida / f"Base para SS {periodo} (diligenciada).xlsx")
    archivos_aza.escribir_formato_ajuste(mes, salida / f"Formato Ajuste Seguridad social {periodo}.xlsx")
    tablero.escribir(mes, salida / f"tablero_{periodo}.json")
    return mes


def main() -> None:
    raiz = Path(sys.argv[1] if len(sys.argv) > 1 else "demo_salida")
    generar(raiz)
    mes = correr(raiz)
    print(f"Periodo {mes.periodo} · fecha límite {mes.fecha_limite}")
    for estado, cuenta in sorted(mes.resumen().items()):
        print(f"  {estado:<22} {cuenta}")
    ind = [v for v in mes.indicador().values() if v is not None]
    print(f"Indicador de oportunidad: {sum(ind)}/{len(ind)}")
    print(f"Borradores de correo: {len(correos.borradores(mes))}")
    print(f"Salidas en: {raiz / mes.periodo}")


if __name__ == "__main__":
    main()
