# Validador de soportes de seguridad social

Proyecto del equipo Error404 para el Reto 6 de Estud-IA (AZA Gestión del Riesgo).

Lee los comprobantes de pago de seguridad social que llegan por correo, los compara con la
liquidación del mes y deja el resultado en un Excel maestro auditable, con borradores de correo
para quien debe corregir.

## Estado

| Parte | Estado |
|---|---|
| Esquema de datos, reglas y estados | Funciona, con pruebas |
| Calendario de días hábiles de Colombia | Funciona, con pruebas |
| Lectura por plantillas (carril 1) | Funciona con el formato ficticio; faltan operadores reales |
| Orden de claves para PDF con contraseña | Funciona, con pruebas |
| Excel maestro y borradores de correo | Funciona en local |
| Inspección con Claude (carril 2) | Diseñado, sin implementar |
| Conexión a Office 365 | Diseñado, sin implementar |
| Datos del tablero (`tablero_AAAA-MM.json`) y verificador de cifras | Funciona, con pruebas |
| Tablero con aprobación de correos | Prototipo visual aparte; estrategia y paso a paso en `docs/TABLERO.md` |

## Empezar

```bash
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q                 # corre las pruebas
python -m validador.demo  # demo de punta a punta con datos ficticios
```

La demo crea `demo_salida/` con una liquidación ficticia, doce prestadores, errores sembrados y el
Excel maestro resultante.

## Estructura

```
src/validador/
  esquema.py          Soporte, Expectativa, Reglas, Estado, Resultado
  reglas.py           Validación determinista de un soporte
  calendario.py       Días hábiles y festivos de Colombia
  expectativas.py     Carga la liquidación del mes
  conciliacion.py     Estado del mes, bitácora y corte
  lectura/            plantillas (carril 1), claves de PDF, inspección con Claude (carril 2)
  adaptadores/        local (demo) y Office 365
  salidas/            Excel maestro, borradores de correo, datos del tablero y verificador de cifras
config/reglas.yaml    Tolerancia, día de corte y columnas de la liquidación
plantillas_operador/  Cómo agregar la plantilla de un operador
docs/                 Instalación, pruebas, operación y soporte
tests/                Pruebas automáticas
```

## Reglas del repositorio

- Ningún dato real en el repositorio. La carpeta `datos_reales/` y los PDF están en `.gitignore`.
- Credenciales solo en `.env`, que tampoco se sube.
- Los cambios entran por solicitud de cambio con las pruebas en verde.

## Documentos

- [Instalación en la infraestructura de AZA](docs/INSTALACION.md)
- [Plan de pruebas](docs/PRUEBAS.md)
- [Operación y soporte](docs/OPERACION.md)
- [Tablero y Claude: estrategia e implementación](docs/TABLERO.md)
