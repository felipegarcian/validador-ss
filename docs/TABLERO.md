# Tablero y Claude: estrategia e implementación paso a paso

Estado: propuesta del equipo, alineada con lo que ya está en el repositorio. Este documento
define qué se construye, en qué orden y con qué barandas, para que cualquier persona de TI (o
Claude Code) lo pueda implementar sin reinterpretar el diseño.

| Fase | Estado |
|---|---|
| 0. Decisiones y aprobaciones | Pendiente (AZA) |
| 1. Contrato de datos del tablero | ✅ `salidas/tablero.py`, `tests/test_tablero.py` |
| 2. Tablero v1 y aprobación de correos | Parcial: JSON en `Salidas/` y verificador de cifras ✅; flujos y página por montar |
| 3. Claude en el tablero (C1, C2) | Pendiente |
| 4. Carril 2 asistido (C3, C4) | ✅ sin API ([CARRIL2_CLAUDE.md](CARRIL2_CLAUDE.md)); falta mostrarlo en el tablero |
| 5. Operación continua | Pendiente |

Documentos relacionados: [AUTOMATIZACION_O365.md](AUTOMATIZACION_O365.md) (flujos de Power
Automate y adaptador de carpeta) y [CARRIL2_CLAUDE.md](CARRIL2_CLAUDE.md) (Claude sin API).

---

## 1. Punto de partida

| Pieza | Hoy | Lo que le falta para el tablero |
|---|---|---|
| Adaptador de carpeta (`adaptadores/carpeta_o365.py`) | Trabaja sobre la biblioteca de SharePoint sincronizada; escribe `Salidas/`, `Correos/pendientes/` y `salud.json` | Nada: ya deja también `Salidas/tablero_AAAA-MM.json` |
| Excel maestro (`salidas/excel_maestro.py`) | Hojas Control, Bitácora, Correos y Contabilidad | Es para auditar, no un contrato de datos: por eso existe el JSON del tablero |
| Aprobación de correos | Flujo 2 de Power Automate: aprobación en Teams y envío desde el buzón compartido | Una vista consolidada del mes y, más adelante, poder editar el texto sin tocar cifras |
| Carril 2 (`lectura/carril2_asistido.py`) | Paquete con datos tapados para el proyecto de Claude de AZA; la respuesta pasa por las mismas reglas | Ver en el tablero qué casos esperan respuesta de Claude o tienen problemas |
| Claude en el tablero | No existe | Resumen del mes y explicación de casos (C1, C2) |
| Roles | Definidos en `INSTALACION.md` | Aplicarlos en la plataforma |

La estrategia se apoya en tres decisiones:

1. **Un contrato de datos único** (`tablero_AAAA-MM.json`) generado por el motor. El tablero
   solo muestra; nunca calcula estados ni cifras.
2. **Claude como asistente de lectura y explicación, nunca de decisión.** Transcribe, explica y
   resume; la regla determinista de `reglas.py` y una persona deciden.
3. **Primero sin API, después con API si se justifica.** Se usa el plan de Claude que AZA ya
   tiene (copiar y pegar guiado, como el carril 2). La variante con API solo se enciende para
   lo que se repite mucho, se llama desde el motor y la clave nunca llega al tablero.

## 2. Principios (no se negocian)

Son los de `CLAUDE.md`, aplicados al tablero:

- **Ninguna IA decide un estado ni calcula una cifra.** Todo número que aparece en el tablero o
  en un correo sale del `Resultado` o de la Base.
- **Nada se envía sin aprobación humana.** El tablero registra quién aprobó y cuándo.
- **Mínimo dato posible a Claude.** Ni nombres, ni cédulas, ni correos, ni teléfonos ni
  direcciones. El carril 2 ya los tapa antes de copiar; la cédula se verifica en el equipo de AZA.
- **Todo deja rastro.** Cada texto generado por Claude queda en la Bitácora con
  `origen = "ia"`, el modelo usado y el identificador de la solicitud.
- **Si Claude falla, el proceso sigue.** Cada uso de Claude tiene un texto de respaldo
  determinista; el tablero nunca queda vacío por un error de la API.

## 3. Arquitectura

```
 Buzón compartido ──Flujo 1──► 01_Entrada/ (PDF + .json)
                                   │
                                   ▼
                   MOTOR (carpeta_o365, cada 10 min, determinista)
                     conciliacion.Mes → reglas.evaluar → Resultado
                     ├─► Salidas/Control_SS_AAAA-MM.xlsx        auditoría
                     ├─► Salidas/tablero_AAAA-MM.json           fuente del tablero
                     ├─► Correos/pendientes/*.json              borradores
                     ├─► 03_Por_revisar/<id>/paquete_claude.txt carril 2 sin API
                     ├─► salud.json                             vigilancia de TI
                     └─► Capa IA con API (opcional, Fase 3, CLAUDE_HABILITADO=1)
                           seudonimiza → Claude → verificador → o texto de respaldo

 Flujo 2: Correos/pendientes → aprobación en Teams → envío desde el buzón → Correos/enviados
 Flujo 4: tablero_AAAA-MM.json → listas «Casos SS» e «Indicadores SS» → página por rol
```

**Un solo camino de envío.** Todo correo sale por el Flujo 2 y solo después de una aprobación.
En la v1 la analista aprueba o rechaza sin editar, así que las cifras no pueden cambiar. Cuando
se permita editar (v2), el texto editado se guarda en `Correos/editados/`; el motor lo compara
con las cifras del borrador original (`verificador.conserva_cifras`) y solo si coinciden lo pasa
a `Correos/pendientes/`. Si no coinciden, lo deja en `Correos/bloqueados/` con la nota «Cambió
una cifra; revisar».

### Plataforma recomendada

| Fase | Plataforma | Por qué |
|---|---|---|
| v1 | Aprobaciones de Teams (Flujo 2) + página de SharePoint con las listas que llena el Flujo 4 | Viene con Office 365; el ingreso con la cuenta de la empresa y los grupos de SharePoint dan los roles |
| v2 | Power Apps sobre las mismas listas, con edición de borradores | Mejor experiencia; el contrato de datos no cambia |
| Opcional | Power BI sobre `tablero_AAAA-MM.json` para Dirección | Tendencias entre meses; requiere licencia |

El contrato de datos es el mismo en todas, por eso la plataforma se puede cambiar sin tocar
el motor.

## 4. Qué muestra el tablero por rol

| Rol | Ve | Puede hacer |
|---|---|---|
| Dirección | Indicadores del mes, tendencia, resumen del mes | Consultar |
| Gestión Humana | Todo lo anterior + casos por estado, revisión manual, carril 2 pendiente, borradores | Aprobar o rechazar borradores (editar en v2); completar el carril 2; confirmar casos de revisión manual |
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
| Borradores por aprobar | archivos en `Correos/pendientes/` | carpeta (Flujo 2) |
| Días hábiles al corte | hoy frente a `Mes.fecha_limite` | `calendario` |
| Lectura por carril | conteo por `Soporte.origen_lectura` (plantilla, ia, manual) | `Mes.soportes` |

## 5. Dónde aporta Claude

| Uso | Para quién | Qué recibe Claude | Qué devuelve | Cómo | Estado |
|---|---|---|---|---|---|
| **C1. Resumen del mes** | Dirección | Solo indicadores agregados; ningún dato de personas | 3 a 5 frases sobre el estado del mes y qué atender | API desde el motor (o paquete para pegar, como el carril 2) | Fase 3 |
| **C2. Explicación del caso** | Gestión Humana | Estado, motivo, IBC requerido, IBC pagado, diferencia, tardío, código de error. Sin nombre ni cédula | Explicación en lenguaje claro y qué sigue según el procedimiento | API desde el motor | Fase 3 |
| **C3. Lectura asistida (carril 2)** | Gestión Humana | Texto de la planilla con cédula, nombre, correo, teléfono y dirección tapados | Campos del `Soporte` en JSON; el motor los valida con las mismas reglas | Sin API: proyecto «Validador SS · Carril 2» | ✅ |
| **C4. Propuesta de plantilla** | TI | El mismo texto tapado y la respuesta ya confirmada | Plantilla YAML en `plantillas_operador/`, probada con `scripts/probar_plantilla.py` | Sin API, mismo proyecto | ✅ |

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
3. **Aprobación de datos para Claude.** AZA confirma que su plan de Claude es de empresa (Team o
   Enterprise) para el carril 2 (C3, C4) y aprueba por escrito los usos C1 y C2 (sin datos
   personales). Revisar las condiciones de retención de
   datos del plan de la API de Anthropic que se contrate.
   *Hecho cuando:* el acta indica qué usos quedan permitidos.
4. **Cuenta de la API (solo para la Fase 3).** El carril 2 no la necesita. Si se aprueban C1 y C2
   con API, crear la clave en la consola de Anthropic a nombre de AZA, con límite de gasto mensual. Guardarla en Azure Key Vault o en las variables de entorno del equipo, nunca
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

8. **Montar los flujos 1, 2 y 3** de [AUTOMATIZACION_O365.md](AUTOMATIZACION_O365.md) y la
   tarea programada del motor (`python -m validador.adaptadores.carpeta_o365 <raíz> --periodo AAAA-MM`).
   *Hecho cuando:* un correo de prueba llega a `01_Entrada/`, el motor lo procesa y su borrador
   se aprueba en Teams y sale del buzón compartido.
9. **JSON del tablero en `Salidas/`.** El adaptador de carpeta llama a `tablero.escribir` en
   cada ejecución, junto al Excel maestro. Se reescribe completo: es idempotente como el resto.
   *Hecho cuando:* `tests/test_carril2.py` encuentra `Salidas/tablero_2026-10.json` con el caso
   leído por Claude contado en `por_origen.ia`. ✅
10. **Verificador de cifras en `src/validador/salidas/verificador.py`** (ya implementado).
    Reconoce montos en pesos (`$1.600.000`, `$ 1.600.000`, `$-174.785`), porcentajes
    (`1,044 %`) y fechas (`09/11/2026`), sin espacios internos:

    ```python
    from validador.salidas import verificador

    verificador.cifras(texto)                         # set de cifras del texto
    verificador.cifras(texto, enteros=True)           # incluye números sueltos ("7 de 12")
    verificador.conserva_cifras(texto, originales)    # correo editado: mismas cifras, ni más ni menos
    verificador.sin_cifras_nuevas(texto, permitidas)  # texto de IA: solo cifras permitidas
    verificador.cifras_nuevas(texto, permitidas)      # las que sobran, para la Bitácora
    ```

    Cada correo del JSON trae en `cifras` las del borrador original. Se usa en la v2 para los
    borradores editados (sección 3) y en la Fase 3 para los textos de IA.
    *Hecho cuando:* hay pruebas con un texto que inventa una cifra, uno que la borra y uno
    correcto. ✅
11. **Flujo 4 · Publicar el tablero** (Power Automate):

    | Paso | Acción | Configuración |
    |---|---|---|
    | Disparador | *Cuando se crea o modifica un archivo* (SharePoint) | Carpeta `Salidas`, nombre que empiece por `tablero_` |
    | 1 | *Obtener contenido del archivo* y *Analizar JSON* | Esquema: el del paso 5 |
    | 2 | *Aplicar a cada uno* sobre `casos` | *Crear o actualizar elemento* en la lista «Casos SS» con clave `Periodo` + `id` |
    | 3 | *Crear o actualizar elemento* | Lista «Indicadores SS», una fila por periodo con oportunidad, habilitados, sin identificar y días al corte |

    Permisos: «Casos SS» solo para `SS-GestionHumana` y `SS-Administrador` (trae nombres y
    cédulas); «Indicadores SS» para todos los grupos.
    *Hecho cuando:* tras una ejecución del motor, las listas muestran lo mismo que el JSON.
12. **Página de SharePoint por rol.** Dirección: tarjetas desde «Indicadores SS». Gestión
    Humana: «Casos SS» filtrable por estado, vista de REVISIÓN MANUAL · L-01 con enlace a la
    carpeta del caso en `03_Por_revisar/`, y enlace a las aprobaciones de Teams. Contabilidad:
    hoja Contabilidad del Excel maestro. Administrador: `salud.json` y la Bitácora.
    *Hecho cuando:* Gestión Humana entiende el estado del mes y sabe qué atender sin abrir el
    Excel.

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

### Fase 4. Carril 2 asistido: C3 y C4 (implementado sin API)

22. **C3 sin API.** ✅ `lectura/carril2_asistido.py` arma el paquete con datos personales tapados,
    el adaptador lo deja en `03_Por_revisar/<id>/paquete_claude.txt`, la analista pega la
    respuesta en `respuesta_claude.txt` y el siguiente ciclo la valida con las mismas reglas
    (`origen_lectura = "ia"`). Si falta algo, `problemas.txt` dice qué pedirle a Claude.
    Configuración del proyecto de Claude y pasos de la analista: [CARRIL2_CLAUDE.md](CARRIL2_CLAUDE.md).
23. **Verlo en el tablero.** Agregar a cada caso del JSON el estado del carril 2 (esperando
    respuesta, con problemas, leído por IA) a partir de la carpeta `03_Por_revisar/`, para que
    Gestión Humana vea en la página qué casos esperan su paso de copiar y pegar.
    *Hecho cuando:* un caso L-01 aparece en la vista de Gestión Humana con su enlace y su
    estado del carril 2.
24. **C4, propuesta de plantilla.** ✅ Con un caso confirmado, `carril2_asistido.generar_paquete_plantilla`
    arma el pedido; Claude responde una plantilla YAML que se guarda en `plantillas_operador/`
    como `borrador`, se prueba con `python -I scripts/probar_plantilla.py` y pasa a `activa` por
    solicitud de cambio. Nunca se guarda el PDF real.
25. **Medir.** `salud.json` cuenta `leidos_por_ia` y el JSON del tablero trae `por_origen`. Ese
    número debe bajar mes a mes a medida que los formatos se vuelven plantillas. Si un mismo
    formato llega más de tres veces, priorizar su plantilla. Una variante con API para C3 solo
    se considera si el volumen lo justifica y con aprobación de AZA para enviar el documento.

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
| El adaptador de carpeta deja el JSON del tablero con el caso del carril 2 (ya corre) | `tests/test_carril2.py` |
| Un borrador editado con cifra cambiada queda en `Correos/bloqueados/` (v2) | `tests/test_carril2.py` |
| La seudonimización no deja pasar nombres ni cédulas | `tests/test_ia.py` |
| Rechazo, error de red o capa apagada usan el respaldo | `tests/test_ia.py` |

## 9. Lista de verificación antes de encender

- [ ] Acta de AZA con los usos de Claude permitidos.
- [ ] Clave de la API fuera del repositorio, con límite de gasto y fecha de revisión.
- [ ] `pytest -q` y `python -m validador.demo` en verde en el equipo de destino.
- [ ] Un mes en modo sombra con el tablero: nada se envía y Gestión Humana compara.
- [ ] Cada rol ve solo lo suyo (probar con una cuenta de cada grupo).
- [ ] Ningún correo sale sin pasar por la aprobación del Flujo 2.
- [ ] (v2) Un borrador editado con una cifra cambiada queda en `Correos/bloqueados/`.
- [ ] Con `CLAUDE_HABILITADO=0` el tablero funciona igual, con textos de respaldo.

## 10. Riesgos y cómo se mitigan

| Riesgo | Mitigación |
|---|---|
| Claude escribe una cifra equivocada | Verificador de cifras; texto de respaldo; etiqueta «generado con IA» |
| Se filtran datos personales | Lista blanca de campos; C3 solo con aprobación; pruebas de seudonimización |
| La analista cambia una cifra al editar un correo (v2) | El motor verifica antes de pasarlo al Flujo 2 y lo bloquea |
| La API no responde el día del corte | Todo uso de Claude es opcional; el respaldo cubre el tablero |
| El costo crece sin control | Límite de gasto, textos guardados, C2 solo para casos nuevos |
| Se cambia la plataforma del tablero | El contrato JSON no depende de la plataforma |
