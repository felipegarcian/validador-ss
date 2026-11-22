# Guía de contribución

Gracias por ayudar a mejorar Validador de soportes de pago de seguridad social. Esta guía describe el flujo para proponer cambios seguros, verificables y fáciles de mantener.

## Antes de empezar

- Revisa el [README](README.md), la documentación de [operación y soporte](docs/OPERACION.md) y, para cambios de lectura, la [guía de plantillas de operadores](plantillas_operador/README.md).
- Para un cambio grande o que modifique el comportamiento esperado, abre primero una incidencia para acordar el alcance.
- No uses datos reales de personas, planillas ni PDF. Usa solo los datos ficticios de `validador.demo` y `tests/fixtures`.
- No incluyas credenciales, archivos `.env`, ni salidas generadas en los cambios.

## Preparar el entorno

Instala el proyecto con sus dependencias de desarrollo:

```bash
python -m pip install -e ".[dev]"
```

Para trabajar en lectores PDF, instala también la dependencia opcional:

```bash
python -m pip install -e ".[dev,pdf]"
```

## Implementar y probar

- Mantén la validación de estados y cifras determinista; no delegues decisiones de negocio a un modelo de IA.
- Si cambia una regla, actualiza `config/reglas.yaml` cuando corresponda y añade una prueba enfocada en `tests/test_reglas.py`.
- Si agregas una plantilla de operador, sigue `plantillas_operador/README.md` y prueba con texto inventado que imite el formato; no agregues el PDF original.
- No sobrescribas la Base para SS original. Conserva el flujo que genera una copia diligenciada.
- Actualiza la documentación cuando cambie el uso, la configuración, el comportamiento o el estado de una integración.

Antes de abrir una solicitud de cambios, ejecuta:

```bash
pytest -q
python -m validador.demo
```

Ambos comandos deben terminar correctamente. GitHub Actions ejecuta estas mismas comprobaciones en cada `push` y `pull_request` mediante `.github/workflows/pruebas.yml`. Si renombras o reemplazas ese flujo, actualiza también el badge de pruebas del README.

## Commits

Usa mensajes breves en inglés o español que sigan [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<tipo>(<alcance opcional>): <descripción en imperativo>
```

Tipos habituales:

- `feat`: funcionalidad nueva.
- `fix`: corrección de un error.
- `docs`: documentación.
- `test`: pruebas.
- `refactor`: cambio interno sin alterar el comportamiento.
- `ci`: integración continua.
- `build` o `chore`: dependencias o tareas de mantenimiento.

Ejemplos: `feat(lectura): agrega plantilla ficticia de operador` y `docs: aclara instalación en Windows`.

## Solicitud de cambios

Abre una solicitud de cambios por cada conjunto coherente de trabajo. Incluye:

- El problema que resuelve y un resumen del cambio.
- Las pruebas y comandos que ejecutaste.
- Cambios relevantes en reglas, configuración, dependencias o documentación.
- Capturas solo si son necesarias para explicar cambios visuales; nunca incluyas información personal o real.

Las comprobaciones de CI deben pasar antes de integrar el cambio. No incluyas datos sensibles en el título, descripción, comentarios ni adjuntos.

## Versiones y registro de cambios

El proyecto usa [Semantic Versioning 2.0.0](https://semver.org/). La versión vigente se define en `pyproject.toml`.

- Mientras la versión sea `0.y.z`, el proyecto se considera inestable; los cambios incompatibles pueden incrementar `y`.
- Una vez en `1.0.0`, incrementa `MAJOR` para cambios incompatibles, `MINOR` para funcionalidad compatible y `PATCH` para correcciones compatibles.
- Registra cambios destinados a usuarios en la sección `Unreleased` de `CHANGELOG.md`, organizados según [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/): `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed` y `Security`.
- Al publicar una versión, mueve los elementos correspondientes desde `Unreleased`, agrega la fecha en formato `AAAA-MM-DD`, actualiza la versión de `pyproject.toml` y crea una etiqueta Git `vX.Y.Z`.
- No agregues entradas al changelog por cambios internos que no afecten a usuarios.

Los cambios en las reglas de validación deben documentar su impacto y contar con pruebas antes de publicarse.
