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

### Changed

- README actualizado con los créditos del equipo y los perfiles de GitHub proporcionados.
- La persona se identifica primero por una cédula de la Base presente en el PDF y después por el nombre del remitente.
