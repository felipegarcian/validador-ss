# Instrucciones para Claude Code en este repositorio

## Qué es

Validador de planillas de seguridad social para AZA Gestión del Riesgo. Implementa el
procedimiento de AZA v3.0 (noviembre 2026). El núcleo es Python puro y no conoce Office 365:
recibe la Base para SS del mes y textos de planillas, y produce estados, el indicador de
oportunidad, borradores de correo (causales 7.1 a 7.5) y los archivos de AZA diligenciados.

Regla central: IBC pagado (el menor entre pensión, salud y riesgos) frente a IBC requerido
(BASE RTTE × 40 %, al peso; Especial: mínimo el SMMLV). Hasta $1.000 por debajo = OK;
cualquier peso por encima = PAGO DE MÁS; más de $1.000 por debajo = PENDIENTE AJUSTE.
Los estados se escriben exactamente como en `esquema.Estado`.

## Reglas que no se rompen

- Nunca escribas ni pidas datos reales de personas. Usa solo los ficticios de `validador.demo` y
  `tests/fixtures`. Los insumos reales viven en `datos_reales/` (ignorada por git) y se prueban con
  `python -I scripts/probar_insumos.py datos_reales/AAAA-MM --periodo AAAA-MM`.
- Nunca se sobrescribe la Base original: se escribe una copia diligenciada.
- La validación es código determinista en `reglas.py`. Ninguna IA decide un estado ni calcula una cifra.
- Los correos salen de plantillas; las cifras salen del `Resultado`. Nada se envía sin aprobación humana.
- Todo cambio debe dejar `pytest -q` y `python -m validador.demo` funcionando.
- Las credenciales van en variables de entorno. No las escribas en código ni en pruebas.

## Tareas frecuentes

**Agregar la plantilla de un operador.** Sigue `plantillas_operador/README.md`: agrega una
`Plantilla` en `src/validador/lectura/plantillas.py` y una prueba con un texto ficticio que
imite el formato. No guardes el PDF real en el repositorio.

**Diagnosticar un error.** Pide el código de error (L-01, L-03, I-01, R-01, R-02, S-01...) y busca su significado
en `docs/OPERACION.md`. Reproduce con un soporte ficticio antes de cambiar código.

**Cambiar una regla.** Los valores están en `config/reglas.yaml`. Si cambia la lógica, edita
`reglas.py` y agrega la prueba del caso nuevo en `tests/test_reglas.py`.

**Trabajar en el tablero o en la capa de Claude.** Sigue `docs/TABLERO.md`, fase por fase. El tablero
solo lee el contrato `tablero_AAAA-MM.json`; Claude solo explica o resume, con datos seudonimizados,
pasa por el verificador de cifras y siempre tiene texto de respaldo. Las pruebas usan un cliente
falso: nunca llaman a la API.

## Comandos

```bash
pip install -e ".[dev]"
pytest -q
python -m validador.demo
```
