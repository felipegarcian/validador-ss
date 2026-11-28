# Disparadores automáticos con Power Automate

Objetivo: que la parte de Office 365 se monte en una tarde, sin registrar aplicaciones ni
dar permisos de Graph al motor. Power Automate, que viene con Office 365 en los planes
empresariales, mueve los correos y los archivos; el motor solo lee y escribe una carpeta.

> PREGUNTAR a TI: que el plan de Office 365 incluya Power Automate con los conectores
> estándar de Outlook, SharePoint y Aprobaciones, y quién crea el buzón compartido.

## Lo que crea TI (complejidad baja)

1. **Buzón compartido** `seguridadsocial@<dominio>`, con acceso para la analista. A partir de
   ese mes los prestadores envían ahí.
2. **Biblioteca de SharePoint** «Seguridad Social» con las carpetas `01_Entrada`,
   `02_Procesados`, `03_Por_revisar`, `Correos/pendientes`, `Correos/enviados` y `Salidas`.
   El motor las crea solo si no existen.
3. **Sincronizar** esa biblioteca con OneDrive en el equipo donde corre el motor.

## Flujo 1 · Recibir planillas

| Paso | Acción de Power Automate | Configuración |
|---|---|---|
| Disparador | *Cuando llega un correo nuevo a un buzón compartido (V2)* | Buzón: el compartido · Incluir adjuntos: Sí · Filtro de asunto: `Seguridad Social` |
| 1 | *Aplicar a cada uno* sobre los adjuntos | Condición: el nombre termina en `.pdf` |
| 2 | *Crear archivo* (SharePoint) | Carpeta `01_Entrada` · Nombre: `@{formatDateTime(triggerOutputs()?['body/receivedDateTime'],'yyyyMMdd-HHmmss')}-@{items('Aplicar_a_cada_uno')?['id']}.pdf` · Contenido: el del adjunto |
| 3 | *Crear archivo* (SharePoint) | Mismo nombre con `.json` · Contenido: `{"remitente": "@{triggerOutputs()?['body/from']}", "recibido": "@{triggerOutputs()?['body/receivedDateTime']}", "asunto": "@{triggerOutputs()?['body/subject']}"}` |
| 4 | *Mover correo (V2)* | A la carpeta «Procesados» del buzón compartido |

Si el remitente llega como correo y no como nombre, el motor lo cruza con el directorio de
prestadores.

## Flujo 2 · Aprobar y enviar correos

| Paso | Acción | Configuración |
|---|---|---|
| Disparador | *Cuando se crea un archivo* (SharePoint) | Carpeta `Correos/pendientes` |
| 1 | *Obtener contenido del archivo* y *Analizar JSON* | Claves: `para`, `asunto`, `cuerpo`, `causal` |
| 2 | *Iniciar y esperar una aprobación* | Tipo: Aprobar o rechazar · Asignado a: la analista · Detalles: el cuerpo del correo. Llega a Teams y Outlook. |
| 3 | Si la respuesta es «Aprobar»: *Enviar un correo desde un buzón compartido (V2)* | Desde: el compartido · Para, Asunto y Cuerpo del JSON |
| 4 | *Mover archivo* | A `Correos/enviados` (si se rechaza, a `Correos/rechazados`) |

Así ningún correo sale sin aprobación y no hay que construir un tablero para aprobar.

## Flujo 3 · Avisos de salud (opcional, recomendado)

- Disparador: *Periódico*, cada día a las 7:00.
- Leer `salud.json`. Publicar en un canal de Teams: procesadas, por revisar, leídas por IA,
  habilitados y errores.
- Si la hora de `ejecucion` tiene más de 2 horas, publicar **«El motor no ha corrido»**.

## Flujo 4 · Publicar el tablero (siguiente paso)

El motor deja en cada ejecución `Salidas/tablero_AAAA-MM.json`. Un cuarto flujo lo pasa a las
listas «Casos SS» e «Indicadores SS» para la página del tablero. Pasos y permisos en
[TABLERO.md](TABLERO.md), Fase 2, paso 11.

## El motor

En el equipo con la biblioteca sincronizada, una tarea programada de Windows cada 10
minutos:

```
python -m validador.adaptadores.carpeta_o365 "C:\Users\<usuario>\<empresa>\Seguridad Social" --periodo 2026-10
```

Cada ejecución es idempotente: reconstruye el mes desde lo recibido, así que si una falla
la siguiente deja todo bien. El periodo se cambia al abrir el mes; más adelante se calcula
solo desde la Base.

Cuando AZA quiera quitar el equipo de en medio, el mismo motor se puede llevar a Azure
Functions o a la API de Graph (docs/INSTALACION.md). Los flujos 2 y 3 no cambian.
