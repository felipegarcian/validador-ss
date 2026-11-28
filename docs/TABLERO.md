# Tablero y Claude: estrategia e implementación paso a paso

Estado: propuesta del equipo. **Fase 1 implementada** (`salidas/tablero.py`, `salidas/verificador.py`,
`tests/test_tablero.py`). El tablero visual sigue como prototipo y el carril 2
(`lectura/inspeccion_claude.py`) no está implementado. Este documento define qué se construye,
en qué orden y con qué barandas, para que cualquier persona de TI (o Claude Code) lo pueda
implementar sin reinterpretar el diseño.

---

## 1. Punto de partida

| Pieza | Hoy | Problema para el tablero |
|---|---|---|
| Excel maestro (`salidas/excel_maestro.py`) | Hojas Control, Bitácora, Correos y Contabilidad | Es una salida para leer, no un contrato de datos: el tablero tendría que adivinar columnas |
| Borradores (`salidas/correos.py`) | Se generan con cifras del `Resultado` | No hay flujo de aprobación ni registro de quién aprobó |
| Claude | Solo previsto para el carril 2 (leer PDF desconocidos) | No hay un papel definido para Claude dentro del tablero |
| Roles | Definidos en `INSTALACION.md` | Falta decidir la plataforma y cómo se aplican |

La estrategia se apoya en tres decisiones:

1. **Un contrato de datos único** (`tablero_AAAA-MM.json`) generado por el motor. El tablero
   solo muestra; nunca calcula estados ni cifras.
2. **Claude como asistente de lectura y explicación, nunca de decisión.** Explica, resume y
   propone; la regla determinista de `reglas.py` y una persona deciden.
3. **Claude se llama solo desde el motor**, con la clave en el servidor. El tablero no habla
   con Claude ni guarda la clave.

## 2. Principios (no se negocian)

Son los de `CLAUDE.md`, aplicados al tablero:

- **Ninguna IA decide un estado ni calcula una cifra.** Todo número que aparece en el tablero o
  en un correo sale del `Resultado` o de la Base.
- **Nada se envía sin aprobación humana.** El tablero registra quién aprobó y cuándo.
- **Mínimo dato posible a Claude.** Ni nombres, ni cédulas, ni correos, salvo en el carril 2
  con aprobación expresa de AZA.
- **Todo deja rastro.** Cada texto generado por Claude queda en la Bitácora con
  `origen = "ia"`, el modelo usado y el identificador de la solicitud.
- **Si Claude falla, el proceso sigue.** Cada uso de Claude tiene un texto de respaldo
  determinista; el tablero nunca queda vacío por un error de la API.

## 3. Arquitectura

```
 Buzón + SharePoint ──► MOTOR (Python, determinista)
                          │  conciliacion.Mes  →  reglas.evaluar  →  Resultado
                          │
                          ├─► Excel maestro (Control_SS_AAAA-MM.xlsx)        ← auditoría
                          ├─► tablero_AAAA-MM.json  (contrato de datos)      ← fuente del tablero
                          └─► Capa IA (opcional, CLAUDE_HABILITADO=1)
                                 · seudonimiza → llama a Claude → verifica cifras
                                 · si algo falla: texto de respaldo
                                 · escribe en el JSON con origen "ia"

 TABLERO (SharePoint / Power Apps) ──lee──► tablero_AAAA-MM.json + lista «Correos SS»
        │ la analista aprueba o rechaza borradores en la lista
        ▼
 MOTOR, siguiente ejecución: toma los aprobados, vuelve a verificar cifras, envía desde el
 buzón compartido y marca «Enviado».
```

Por qué el motor envía y no Power Automate: así la verificación de cifras (sección 6) corre en
código probado justo antes de enviar, y el permiso de envío queda en una sola aplicación.

### Plataforma recomendada

| Fase | Plataforma | Por qué |
|---|---|---|
| v1 | Página de SharePoint + lista «Correos SS» + Excel en línea | Sin licencias adicionales; el ingreso con la cuenta de la empresa y los grupos de SharePoint dan los roles |
| v2 | Power Apps sobre la misma lista y el mismo JSON | Mejor experiencia de aprobación, sin cambiar el contrato de datos |
| Alternativa | Aplicación web propia | Solo si AZA no tiene Power Platform; requiere hospedaje y mantenimiento |

El contrato de datos es el mismo en las tres, por eso la plataforma se puede cambiar sin tocar
el motor.

## 4. Qué muestra el tablero por rol

| Rol | Ve | Puede hacer |
|---|---|---|
| Dirección | Indicadores del mes, tendencia, resumen del mes | Consultar |
| Gestión Humana | Todo lo anterior + casos por estado, revisión manual, borradores | Aprobar, rechazar o editar el texto de borradores; confirmar casos de revisión manual |
| Contabilidad | Hoja de habilitados para pago | Consultar y descargar |
| Administrador | Reglas, plantillas, bitácora técnica, costo de Claude | Cambiar `config/reglas.yaml` y plantillas por solicitud de cambio |

### Indicadores (todos calculados por el motor)

| Indicador | Cálculo | Fuente |
|---|---|---|
| Oportunidad | suma de `Resultado.indicador` / prestadores con indicador no vacío | `esquema.Resultado.indicador` |
| Habilitados para pago | prestadores con `Resultado.habilita` / prestadores con honorarios | `esquema.HABILITAN` |
| Casos por estado | conteo por `Estado` | `Mes.estados` |
| Revisión manual por código | conteo por `codigo_error` (L-01, L-04, R-02...) | `Resultado.codigo_error` |
| Sin identificar | `len(Mes.sin_identificar)` | `conciliacion.Mes` |
| Borradores por aprobar | borradores sin «Aprobado por» | lista «Correos SS» |
| Días hábiles al corte | hoy frente a `Mes.fecha_limite` | `calendario` |
| Lectura por carril | conteo por `Soporte.origen_lectura` (plantilla, ia, manual) | `Mes.soportes` |

## 5. Dónde aporta Claude

| Uso | Para quién | Qué recibe Claude | Qué devuelve | Riesgo | Fase |
|---|---|---|---|---|---|
| **C1. Resumen del mes** | Dirección | Solo indicadores agregados y conteos; ningún dato de personas | 3 a 5 frases sobre el estado del mes y qué atender | Bajo | 3 |
| **C2. Explicación del caso** | Gestión Humana | Estado, motivo, IBC requerido, IBC pagado, diferencia, tardío, código de error. Sin nombre ni cédula | Explicación en lenguaje claro de por qué quedó así y qué sigue según el procedimiento | Bajo | 3 |
| **C3. Lectura asistida (carril 2)** | Gestión Humana | El PDF que ninguna plantilla leyó | Propuesta de campos del `Soporte`; la analista confirma campo a campo | Medio: envía un documento con datos personales | 4, con aprobación de AZA |
| **C4. Propuesta de plantilla** | TI | Texto del PDF anonimizado | Una `Plantilla` y su prueba, por solicitud de cambio | Bajo: pasa por `pytest` y revisión | 4 |

Lo que Claude **no** hace en ninguna fase: decidir o cambiar un estado, calcular una cifra,
escribir cifras en un correo, enviar un correo, editar la Base.

## 6. Barandas técnicas

1. **Verificador de cifras.** Todo número en un texto de Claude debe existir en los datos que se
   le enviaron. Si aparece uno nuevo, el texto se descarta y se usa el de respaldo. La misma
   función se usa antes de enviar un correo aprobado: si la analista cambió una cifra al
   editar, el envío se bloquea y el caso vuelve a «Por revisar».
2. **Seudonimización.** Antes de llamar a Claude se arma un diccionario solo con los campos
   permitidos (lista blanca, no lista negra). `observaciones` y `motivo` libres de nombres; si
   hay duda, no se envían.
3. **Interruptores.** `CLAUDE_HABILITADO=1` enciende la capa; `CLAUDE_USOS=C1,C2` elige qué
   usos. Por defecto todo apagado.
4. **Prompts versionados** en `src/validador/ia/prompts/` con número de versión. El número
   queda en la Bitácora para saber qué prompt produjo cada texto.
5. **Rechazos y errores.** Si la respuesta termina con `stop_reason == "refusal"`, si hay error
   de red o si el verificador falla, se usa el texto de respaldo y se anota en la Bitácora.
6. **Costo acotado.** C1 corre una vez por ejecución del motor solo si cambiaron los
   indicadores; C2 solo para casos nuevos o que cambiaron de estado. El texto se guarda y no se
   vuelve a pedir.
7. **Pruebas sin red.** Las pruebas automáticas usan un cliente falso; nunca llaman a la API ni
   necesitan clave.

---

## 7. Implementación paso a paso

Cada paso termina con «Hecho cuando». No se pasa al siguiente sin `pytest -q` y
`python -m validador.demo` en verde.

### Fase 0. Decisiones y aprobaciones (AZA, 1 semana)

1. **Plataforma del tablero.** Confirmar SharePoint + lista para la v1 (sección 3).
   *Hecho cuando:* queda escrito en este documento.
2. **Grupos de SharePoint por rol.** Crear `SS-Direccion`, `SS-GestionHumana`,
   `SS-Contabilidad`, `SS-Administrador` y asignar personas.
   *Hecho cuando:* cada persona entra y ve solo lo de su rol.
3. **Aprobación de datos para Claude.** AZA aprueba por escrito los usos C1 y C2 (sin datos
   personales) y decide si aprueba C3 (envía PDF). Revisar las condiciones de retención de
   datos del plan de la API de Anthropic que se contrate.
   *Hecho cuando:* el acta indica qué usos quedan permitidos.
4. **Cuenta de la API.** Crear la clave en la consola de Anthropic a nombre de AZA, con límite de
   gasto mensual. Guardarla en Azure Key Vault o en las variables de entorno del equipo, nunca
   en el repositorio.
   *Hecho cuando:* la clave existe y tiene fecha de revisión en el calendario de TI.

### Fase 1. Contrato de datos del tablero (desarrollo, 3 a 4 días)

5. **Crear `src/validador/salidas/tablero.py`** con una función `construir(mes) -> dict` y otra
   `escribir(mes, ruta) -> Path`. Estructura mínima:

   ```json
   {
     "version": 1,
     "periodo": "2026-10",
     "generado": "2026-11-07T10:15:00",
     "fecha_limite": "2026-11-07",
     "indicadores": {
       "oportunidad": {"cumplen": 5, "total": 13, "valor": 0.3846},
       "habilitados": {"cumplen": 6, "total": 13, "valor": 0.4615},
       "por_estado": {"OK": 5, "PENDIENTE AJUSTE": 1, "REVISIÓN MANUAL": 3},
       "por_codigo": {"L-01": 1, "R-01": 1, "R-02": 1},
       "por_origen": {"plantilla": 11},
       "sin_identificar": 0,
       "dias_habiles_al_corte": 0
     },
     "casos": [
       {"id": "c-01", "cedula": "...", "nombre": "...", "estado": "PENDIENTE AJUSTE",
        "motivo": "...", "ibc_requerido": 1600000, "ibc_pagado": 1500000,
        "diferencia": -100000, "tardio": false, "codigo_error": null,
        "habilita": false, "indicador": 0, "aviso_riesgo": false, "observaciones": [],
        "riesgo": "II", "especial": false, "base_rtte": 6850000, "fecha_recibido": "2026-11-04",
        "periodo_soporte": "2026-10", "operador": "SuAporte", "numero_planilla": "70000004",
        "origen_lectura": "plantilla", "explicacion": null, "explicacion_origen": null}
     ],
     "correos": [
       {"id": "m-01", "caso": "c-01", "para": "...", "causal": "7.3",
        "asunto": "...", "cuerpo": "...", "cifras": ["$1.600.000", "$1.500.000"]}
     ],
     "resumen": {"texto": null, "origen": null}
   }
   ```

   Reglas: los valores salen de `Mes.estados`, `Mes.expectativas`, `Mes.sin_identificar` y
   `correos.borradores(mes)`; `id` es estable dentro del mes; `cifras` guarda las cifras del
   borrador original para el verificador.
   Los soportes sin identificar van al final de `casos` con `id` s-NN y `cedula` nula. Los días
   hábiles al corte salen de `calendario.dias_habiles_hasta`.
   *Hecho cuando:* la demo escribe `demo_salida/2026-10/tablero_2026-10.json`. ✅
6. **Pruebas en `tests/test_tablero.py`:** los conteos cuadran con el Excel maestro; el
   indicador de oportunidad excluye SIN HONORARIOS; un caso sin identificar aparece en
   `casos` con `habilita = false`; el JSON es válido y estable entre dos ejecuciones iguales.
   *Hecho cuando:* `pytest -q` pasa. ✅
7. **Llamar a `tablero.escribir` desde `demo.py`** junto al Excel maestro. ✅

### Fase 2. Tablero v1 y aprobación de correos (TI + desarrollo, 1 a 2 semanas)

8. **Lista «Correos SS» en el sitio de seguridad social.** Columnas: `IdCorreo`, `Periodo`,
   `Caso`, `Para`, `Causal`, `Asunto`, `Cuerpo` (texto multilínea), `Cifras` (texto),
   `Estado` (Borrador, Aprobado, Rechazado, Bloqueado, Enviado), `AprobadoPor` (persona),
   `FechaAprobacion`, `FechaEnvio`, `Nota`. Permisos: edita `SS-GestionHumana`; el resto, sin
   acceso.
   *Hecho cuando:* la lista existe con esos permisos.
9. **Adaptador en `adaptadores/office365.py`:** `publicar_borradores(sitio, correos)` crea o
   actualiza filas en estado Borrador (sin pisar las que ya estén Aprobadas o Enviadas) y
   `correos_aprobados(sitio)` devuelve las Aprobadas. Probar con un adaptador falso en
   `adaptadores/local.py`.
   *Hecho cuando:* la demo local simula aprobar dos correos y el motor los procesa.
10. **Verificador de cifras en `src/validador/salidas/verificador.py`** (adelantado de la
    Fase 2; ya implementado). Reconoce montos en pesos (`$1.600.000`, `$ 1.600.000`,
    `$-174.785`), porcentajes (`1,044 %`) y fechas (`09/11/2026`), sin espacios internos:

    ```python
    from validador.salidas import verificador

    verificador.cifras(texto)                         # set de cifras del texto
    verificador.cifras(texto, enteros=True)           # incluye números sueltos ("7 de 12")
    verificador.conserva_cifras(texto, originales)    # correo aprobado: mismas cifras, ni más ni menos
    verificador.sin_cifras_nuevas(texto, permitidas)  # texto de IA: solo cifras permitidas
    verificador.cifras_nuevas(texto, permitidas)      # las que sobran, para la Bitácora
    ```

    Cada correo del JSON trae en `cifras` las del borrador original; el paso 11 las usa con
    `conserva_cifras`. Los textos de IA (C1, C2) usan `sin_cifras_nuevas`, que por defecto
    también revisa números sueltos.
    *Hecho cuando:* hay pruebas con un texto que inventa una cifra, uno que la borra y uno
    correcto. ✅
11. **Envío de aprobados.** En cada ejecución, el motor toma los Aprobados, pasa el verificador,
    envía desde el buzón compartido como respuesta en el hilo original y marca Enviado con la
    fecha. Si el verificador falla, marca Bloqueado con la nota «Cambió una cifra; revisar».
    Requiere el permiso de envío limitado al buzón compartido (ver `INSTALACION.md`, paso 4).
    *Hecho cuando:* en el buzón de pruebas llega un correo aprobado y uno con cifra cambiada
    queda Bloqueado.
12. **Página de SharePoint.** Una página por rol con: tarjetas de indicadores (desde el JSON),
    tabla de casos filtrable por estado, vista de la lista «Correos SS» filtrada en Borrador,
    y el enlace al Excel maestro.
    *Hecho cuando:* Gestión Humana aprueba un correo desde la página sin abrir el Excel.

### Fase 3. Claude en el tablero: C1 y C2 (desarrollo, 1 semana)

13. **Dependencia opcional.** En `pyproject.toml`, agregar `ia = ["anthropic>=1"]` en
    `[project.optional-dependencies]`. Variables nuevas en `.env.example`:

    ```
    CLAUDE_HABILITADO=0
    CLAUDE_USOS=C1,C2
    CLAUDE_MODELO=claude-opus-5-5
    ANTHROPIC_API_KEY=
    ```

14. **Módulo `src/validador/ia/`** con `cliente.py`, `seudonimo.py`, `resumen.py` (C1),
    `explicacion.py` (C2) y `prompts/` con `resumen_v1.md` y `explicacion_v1.md`. Esqueleto de
    la llamada:

    ```python
    import os
    import anthropic

    MODELO = os.environ.get("CLAUDE_MODELO", "claude-opus-5-5")

    def pedir(sistema: str, datos: str, cliente: anthropic.Anthropic | None = None) -> tuple[str | None, dict]:
        """Devuelve (texto, traza). texto es None si hubo rechazo o error: usar el respaldo."""
        cliente = cliente or anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno
        try:
            r = cliente.beta.messages.create(
                model=MODELO,
                max_tokens=2000,
                output_config={"effort": "low"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                system=sistema,
                messages=[{"role": "user", "content": datos}],
            )
        except anthropic.APIError as e:
            return None, {"error": type(e).__name__}
        traza = {"modelo": r.model, "request_id": r._request_id, "stop_reason": r.stop_reason}
        if r.stop_reason == "refusal":
            return None, traza
        texto = "".join(b.text for b in r.content if b.type == "text").strip()
        return texto or None, traza
    ```

    Notas: `effort: "low"` basta para resumir y explicar; los `fallbacks` reintentan en otro
    modelo si el primero rechaza la solicitud. Las pruebas pasan un cliente falso por el
    parámetro `cliente`.
15. **Seudonimización (lista blanca).** `seudonimo.caso(resultado)` devuelve solo `estado`,
    `motivo`, `ibc_requerido`, `ibc_pagado`, `diferencia`, `tardio` y `codigo_error`, con las
    cifras ya formateadas por `correos.pesos`. Prueba: ningún nombre ni cédula de la demo
    aparece en lo que se enviaría.
16. **C1, resumen del mes.** Entrada: `indicadores` del JSON y la fecha límite. Prompt: «Eres
    analista de Gestión Humana. Resume en 3 a 5 frases, en español, el estado del mes y qué
    debe atender primero el equipo. Usa solo las cifras que aparecen en los datos; no calcules
    cifras nuevas.» Salida: `resumen.texto`, `resumen.origen = "ia"`. Respaldo: frase armada
    con plantilla («7 de 12 prestadores habilitados; 2 pendientes de ajuste...»).
17. **C2, explicación del caso.** Solo para casos que no están en OK. Entrada: el diccionario
    seudonimizado y el texto de la sección pertinente del procedimiento (estados y causales,
    sin datos de personas). Salida: `casos[i].explicacion`. Respaldo: el `motivo` del
    `Resultado`.
18. **Verificar y anotar.** Cada texto pasa `verificador` (subconjunto de cifras permitidas). Se
    anota en la Bitácora: evento `IA`, uso (C1/C2), versión del prompt, modelo, `request_id` y
    si se usó el respaldo.
19. **Pruebas en `tests/test_ia.py`** con un cliente falso: texto correcto se acepta; texto
    con una cifra inventada se descarta; rechazo y error de red usan el respaldo;
    `CLAUDE_HABILITADO=0` no llama al cliente.
    *Hecho cuando:* `pytest -q` pasa sin red y sin clave.
20. **Evaluación con la demo.** Con la clave de pruebas, correr C1 y C2 sobre la demo y revisar
    a mano con Gestión Humana: ¿la explicación es correcta según el procedimiento?, ¿se
    entiende sin ayuda? Guardar el resultado en `docs/evaluaciones/AAAA-MM.md`.
    *Hecho cuando:* Gestión Humana aprueba al menos 9 de cada 10 explicaciones.
21. **Mostrar en el tablero** el resumen arriba de los indicadores y la explicación al abrir un
    caso, siempre con la etiqueta «Texto generado con IA, revisar» cuando `origen = "ia"`.

### Fase 4. Carril 2 asistido: C3 y C4 (solo con aprobación de AZA)

22. **Implementar `inspeccion_claude.identificar`** enviando el PDF como bloque `document` y
    pidiendo los campos de `Soporte` en JSON. Marcar `origen_lectura = "ia"`. El `Soporte`
    pasa por `reglas.evaluar` como cualquier otro.
23. **Confirmación humana.** En el tablero, el caso aparece en REVISIÓN MANUAL con los campos
    propuestos junto al PDF; la analista confirma o corrige campo a campo. Solo al confirmar se
    re-evalúa y se cambia el estado (`origen_lectura = "manual"` si corrigió algo).
24. **C4, propuesta de plantilla.** TI usa Claude Code con `plantillas_operador/README.md`: crea
    la `Plantilla`, un texto ficticio que imita el formato y su prueba, y abre una solicitud
    de cambio. Nunca se guarda el PDF real.
25. **Medir.** En el tablero del administrador: porcentaje de soportes por carril y cuántos
    campos de C3 corrigió la analista. Si las correcciones pasan de 15 %, apagar C3 y
    priorizar plantillas.

### Fase 5. Operación continua

26. **Revisión mensual (30 minutos, Gestión Humana + TI):** indicadores del mes, correos
    bloqueados, explicaciones marcadas como incorrectas, costo de la API y formatos nuevos.
27. **Cambiar un prompt** es un cambio de código: nueva versión del archivo, prueba, evaluación
    del paso 20 y solicitud de cambio.
28. **Alertas** (sumar a las de `OPERACION.md`): más de 3 textos de IA descartados por el
    verificador en un día; gasto de la API por encima del 80 % del límite; correo Aprobado sin
    enviar por más de una ejecución.

---

## 8. Pruebas que se agregan a `PRUEBAS.md`

| Qué prueba | Archivo |
|---|---|
| El JSON del tablero cuadra con el Excel maestro (ya corre) | `tests/test_tablero.py` |
| El verificador detecta cifras inventadas o borradas (ya corre) | `tests/test_tablero.py` |
| Un correo aprobado con cifra cambiada queda Bloqueado | `tests/test_flujo.py` |
| La seudonimización no deja pasar nombres ni cédulas | `tests/test_ia.py` |
| Rechazo, error de red o capa apagada usan el respaldo | `tests/test_ia.py` |

## 9. Lista de verificación antes de encender

- [ ] Acta de AZA con los usos de Claude permitidos.
- [ ] Clave de la API fuera del repositorio, con límite de gasto y fecha de revisión.
- [ ] `pytest -q` y `python -m validador.demo` en verde en el equipo de destino.
- [ ] Un mes en modo sombra con el tablero: nada se envía y Gestión Humana compara.
- [ ] Cada rol ve solo lo suyo (probar con una cuenta de cada grupo).
- [ ] Un correo con cifra editada queda Bloqueado en el buzón de pruebas.
- [ ] Con `CLAUDE_HABILITADO=0` el tablero funciona igual, con textos de respaldo.

## 10. Riesgos y cómo se mitigan

| Riesgo | Mitigación |
|---|---|
| Claude escribe una cifra equivocada | Verificador de cifras; texto de respaldo; etiqueta «generado con IA» |
| Se filtran datos personales | Lista blanca de campos; C3 solo con aprobación; pruebas de seudonimización |
| La analista cambia una cifra al editar un correo | El motor verifica antes de enviar y bloquea |
| La API no responde el día del corte | Todo uso de Claude es opcional; el respaldo cubre el tablero |
| El costo crece sin control | Límite de gasto, textos guardados, C2 solo para casos nuevos |
| Se cambia la plataforma del tablero | El contrato JSON no depende de la plataforma |
