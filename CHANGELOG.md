# Registro de cambios

Este archivo sigue [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) y el proyecto usa [Semantic Versioning 2.0.0](https://semver.org/).

## [Unreleased]

### Added

- Licencia MIT, guía de contribución y política de versionado.
- Diagrama Mermaid del flujo funcional objetivo en el README.
- Carril 2 sin API: paquete con datos personales tapados para pegar en el Claude de AZA; la respuesta se valida con las mismas reglas y avisa en lenguaje simple qué falta.
- Plantillas de operador en YAML y `scripts/probar_plantilla.py` para probarlas antes de activarlas.
- Adaptador de carpeta (`python -m validador.adaptadores.carpeta_o365`) para trabajar sobre SharePoint sincronizado con Power Automate, con `salud.json` por ejecución.
- Guías `docs/CARRIL2_CLAUDE.md` y `docs/AUTOMATIZACION_O365.md`.
- Estrategia del tablero con Claude y paso a paso de implementación en `docs/TABLERO.md`: contrato de datos, roles, indicadores, usos C1 a C4 y barandas.
- Datos del tablero en `tablero_AAAA-MM.json` (`salidas/tablero.py`): indicadores, casos y correos enlazados a su caso. Lo escriben la demo y el adaptador de carpeta en `Salidas/`.
- Verificador de cifras (`salidas/verificador.py`) para comprobar que un correo editado o un texto de IA no cambie ni invente cifras.
- `calendario.dias_habiles_hasta` para los días hábiles que faltan al corte.

### Changed

- README actualizado con los créditos del equipo y los perfiles de GitHub proporcionados.
- La persona se identifica primero por una cédula de la Base presente en el PDF y después por el nombre del remitente.
