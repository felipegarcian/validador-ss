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
| L-04 | PDF con contraseña que no abre con ninguna cédula de la Base ni del correo (procedimiento 4.3) | Revisar y enviar el borrador que pide la contraseña. Si el remitente no está en la Base, aparece al final de la hoja Control como «SIN IDENTIFICAR» y el borrador va a su dirección; si no hay dirección, completarla a mano |
| I-01 | La persona no está en la Base del mes | Agregar línea al final de la Base (procedimiento 4.4) o verificar el remitente |
| R-01 | Tipo de cotizante distinto de 59 | La analista revisa; puede ser válido según la tabla de parámetros |
| R-02 | Prestador Especial | La analista confirma el estado calculado (regla del SMMLV) |
| S-01 | Sin acceso al buzón, a SharePoint o a la ruta P:\ | TI revisa permisos y credencial |
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
