# Plantillas por operador de planilla

Cada operador (Aportes en Línea, SOI, Mi Planilla, ARUS, Simple, Asopagos) entrega un PDF con
diseño distinto. Los datos son los mismos; cambia dónde están. Una plantilla dice cómo
reconocer el formato y dónde está cada campo.

## Agregar un operador

1. Consigue un comprobante de ejemplo. No lo subas al repositorio.
2. Extrae su texto: `python -c "import pdfplumber,sys; print(pdfplumber.open(sys.argv[1]).pages[0].extract_text())" archivo.pdf`
3. En `src/validador/lectura/plantillas.py` agrega una función `_extraer_<operador>` y una
   entrada en `REGISTRO` con la frase que identifica al operador.
4. Escribe una prueba con un texto ficticio que imite el formato (nombres y cédulas inventados).
5. Corre `pytest -q`.

## Campos que debe llenar

`cedula`, `nombre`, `periodo` (AAAA-MM, el **periodo de cotización**), `pagado` (verdadero solo
si la planilla dice PAGADO), `tipo_empresa`, `tipo_planilla`, `tipo_cotizante`, `ibc_pension`,
`ibc_salud`, `ibc_riesgos`, `tarifa_arl`, `intereses_mora`, `fecha_pago`, `numero_planilla`,
`operador`. El IBC pagado es el menor de los tres IBC (procedimiento 4.5).

Si un formato no trae IBC (por ejemplo, un comprobante de pago bancario), deja los IBC en
`None`: el sistema lo manda a REVISIÓN MANUAL en vez de suponer.

## Estado

| Operador | Plantilla |
|---|---|
| SuAporte / Enlace Operativo, "AUTOLIQUIDACION CONSOLIDADA" | Lista. 5 de 5 planillas reales leídas (nov 2026) |
| Enlace Operativo, comprobante "Información de la Planilla Pagada" | Lista. No trae IBC: va a revisión |
| Compensar, "PLANILLA INTEGRADA DE AUTOLIQUIDACION" | Lista para detectar pre-planillas sin pagar. Falta ver una pagada |
| Aportes en Línea, SOI, Mi Planilla, ARUS, Simple, Asopagos | Pendientes: faltan ejemplos (el procedimiento menciona otros operadores) |

Las planillas reales vinieron cifradas, pero 6 de 7 abrían **sin clave** (solo restringen
copiar e imprimir). Una sí pedía clave de usuario.
