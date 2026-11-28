# Plan de pruebas

## Nivel 1: pruebas automáticas (ya corren)

`pytest -q` ejecuta, sin datos reales:

| Qué prueba | Archivo |
|---|---|
| Regla central y tolerancia de $1.000 en ambos sentidos | `tests/test_reglas.py` |
| Pago menor, pago mayor, planilla sin pagar, otro mes, otro archivo | `tests/test_reglas.py` |
| Cédula fuera de la liquidación y campos faltantes | `tests/test_reglas.py` |
| Entrega tardía | `tests/test_reglas.py` |
| Quinto día hábil con festivos de Colombia | `tests/test_flujo.py` |
| Lectura por plantilla y formato desconocido | `tests/test_flujo.py` |
| Orden de claves para PDF con contraseña | `tests/test_flujo.py` |
| Ciclo completo: liquidación, soportes, corte, Excel maestro | `tests/test_flujo.py` |
| Borrador de correo con las cifras de la validación | `tests/test_flujo.py` |
| Contrato JSON del tablero: cuadra con el Excel, enlaza correos, es estable | `tests/test_tablero.py` |
| Verificador de cifras: detecta cifras cambiadas, borradas o inventadas | `tests/test_tablero.py` |

GitHub las corre en cada cambio (`.github/workflows/pruebas.yml`).

## Nivel 2: demo con errores sembrados

`python -m validador.demo` genera doce prestadores ficticios con un caso de cada tipo y
verifica a la vista que cada uno cae en el estado correcto.

## Nivel 3: prueba con meses históricos (pendiente, requiere a AZA)

1. AZA crea un buzón de pruebas en su Office 365.
2. Gestión Humana reenvía allí, como adjunto, los correos de dos o tres meses cerrados.
3. Contabilidad deja las liquidaciones de esos meses en una carpeta de prueba.
4. El sistema procesa en modo sombra: no escribe a nadie.
5. Se compara con lo que decidió la auxiliar en su momento.

Métrica: soportes con todos los campos correctos sobre el total.

| Resultado | Decisión |
|---|---|
| Más de 85 % | Continuar |
| Entre 60 y 85 % | Agregar plantillas y encender el carril 2 |
| Menos de 60 % | Replantear la lectura |

Los umbrales son una propuesta del equipo.

## Nivel 4: aceptación con la empresa

- [ ] Gestión Humana reconoce cada estado y su motivo sin explicación.
- [ ] Contabilidad puede usar la hoja de valores sin digitar.
- [ ] Un correo de pago menor muestra la diferencia correcta.
- [ ] Un PDF con contraseña se abre con la cédula.
- [ ] Una planilla sin pagar no queda habilitada.

## Lo que todavía no tiene prueba

Lectura de PDF reales, conexión a Office 365, escritura en un Excel abierto, inspección con
Claude y tablero. Las pruebas previstas para el tablero y la capa de Claude están en
[TABLERO.md](TABLERO.md), sección 8.
