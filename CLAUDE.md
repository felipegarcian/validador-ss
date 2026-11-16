# Instrucciones para Claude Code en este repositorio

## Qué es

Validador de soportes de seguridad social para AZA Gestión del Riesgo. El núcleo es Python puro
y no conoce Office 365: recibe una liquidación y textos de comprobantes, y produce estados.

## Reglas que no se rompen

- Nunca escribas ni pidas datos reales de personas. Usa solo los ficticios de `validador.demo`.
- La validación es código determinista en `reglas.py`. Ninguna IA decide un estado ni calcula una cifra.
- Los correos salen de plantillas; las cifras salen del `Resultado`. Nada se envía sin aprobación humana.
- Todo cambio debe dejar `pytest -q` y `python -m validador.demo` funcionando.
- Las credenciales van en variables de entorno. No las escribas en código ni en pruebas.

## Tareas frecuentes

**Agregar la plantilla de un operador.** Sigue `plantillas_operador/README.md`: agrega una
`Plantilla` en `src/validador/lectura/plantillas.py` y una prueba con un texto ficticio que
imite el formato. No guardes el PDF real en el repositorio.

**Diagnosticar un error.** Pide el código de error (L-01, I-01, S-01...) y busca su significado
en `docs/OPERACION.md`. Reproduce con un soporte ficticio antes de cambiar código.

**Cambiar una regla.** Los valores están en `config/reglas.yaml`. Si cambia la lógica, edita
`reglas.py` y agrega la prueba del caso nuevo en `tests/test_reglas.py`.

## Comandos

```bash
pip install -e ".[dev]"
pytest -q
python -m validador.demo
```
