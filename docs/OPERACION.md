# Operación y soporte

## Niveles

| Nivel | Quién | Qué resuelve | Meta propuesta |
|---|---|---|---|
| 0 | El sistema | Detecta, clasifica y deja rastro en la bitácora | Inmediato |
| 1 | Gestión Humana con Claude | Casos de negocio y revisión manual | El mismo día |
| 2 | TI con Claude Code | Errores de lectura o de sistema que se repiten | 2 días hábiles |
| 3 | Consultores | Cambios de reglas o de arquitectura | Según acuerdo |

## Catálogo de errores

| Código | Significa | Primer paso |
|---|---|---|
| L-01 | Ninguna plantilla reconoce el formato | Registrar el caso a mano; pedir la plantilla a TI |
| L-02 | PDF sin texto legible o que no abre | Pedir al prestador el PDF original del operador |
| L-03 | Faltan campos obligatorios | Abrir el PDF y comparar con la fila |
| I-01 | Cédula fuera de la liquidación | Verificar con Contabilidad si falta en el Excel |
| S-01 | Sin acceso al buzón o a SharePoint | TI revisa permisos y credencial |
| S-02 | Excel maestro bloqueado | Cerrar el archivo; el sistema reintenta |

## Qué vigila TI

- Resumen diario: última ejecución, soportes procesados, casos en revisión, errores.
- Alertas: más de un día sin ejecución; falla de permisos; más de 10 casos en revisión.
- Vencimiento de la credencial de la aplicación.

## Cómo pedir ayuda a Claude sin exponer datos

Compartir el código de error y el texto del motivo. No compartir el PDF ni la fila del
prestador, salvo que AZA lo haya aprobado para su plan de Claude.

## Agregar un operador nuevo

Ver `plantillas_operador/README.md`. Ningún cambio se instala si `pytest -q` falla.
