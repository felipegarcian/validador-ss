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

`cedula`, `nombre`, `periodo` (AAAA-MM), `valor_pagado`, `pagado` (verdadero solo si el
comprobante dice que la planilla está pagada), `fecha_pago`, `numero_planilla`, `operador`.

## Estado

| Operador | Plantilla |
|---|---|
| Formato ficticio de la demo | Lista |
| Operadores reales | Pendientes: faltan comprobantes de ejemplo |
