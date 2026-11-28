# Carril 2 con el Claude que AZA ya tiene

Cuando llega una planilla de un formato que ninguna plantilla conoce, el sistema no se
detiene ni adivina: prepara un paquete para que Claude la lea. No se necesita API ni
contrato nuevo; se usa el plan de Claude que AZA ya tiene.

## Configuración, una sola vez (10 minutos)

1. En Claude, crea un proyecto llamado **Validador SS · Carril 2**.
2. En las instrucciones del proyecto pega el texto del recuadro de abajo.
3. Sube como conocimiento del proyecto el *Procedimiento de Validación de Seguridad Social*
   (para que Claude entienda los términos). No subas la Base ni planillas.
4. Comparte el proyecto con la analista de Gestión Humana y con TI.

```
Eres el asistente de lectura del Validador de seguridad social de AZA.
Vas a recibir el texto de planillas PILA con los datos personales tapados ([CEDULA],
[NOMBRE], [CORREO]...). Tu trabajo es transcribir campos, no decidir.
- Responde siempre y solo con un bloque ```json con las claves que pide el mensaje.
- Si un dato no aparece, escribe null. Nunca lo deduzcas ni lo calcules.
- Los IBC van como número entero, sin puntos ni signo $.
- "pagado" es true solo si el documento dice PAGADA o PAGADO; una pre-planilla es false.
- El periodo es el de cotización de pensión, en formato AAAA-MM.
- Si te piden una plantilla YAML, usa exactamente el formato del mensaje y verifica que
  cada expresión regular devuelva el valor confirmado.
```

Antes de empezar, confirma con TI que el plan de Claude de AZA es de empresa (Team o
Enterprise) y que su configuración de datos es la que la empresa aprobó.

## Lo que hace la analista: cuatro pasos

El sistema deja cada caso en `03_Por_revisar/<código del caso>/` y lo muestra en el tablero
como **REVISIÓN MANUAL · L-01**.

1. Abre `paquete_claude.txt` y **copia todo** el texto.
2. Pégalo en un chat nuevo del proyecto **Validador SS · Carril 2**.
3. Copia la respuesta completa de Claude (el bloque con llaves `{ }`).
4. Pégala en `respuesta_claude.txt` en la misma carpeta y guarda.

En el siguiente ciclo, unos minutos después, el sistema:
- valida la respuesta con las mismas reglas del carril 1;
- si está bien, calcula el estado y el caso desaparece de la lista;
- si falta algo, crea `problemas.txt` con lo que hay que pedirle a Claude, en palabras
  simples. Ejemplo: *«Falta el IBC de salud. Pídele a Claude: Busca de nuevo el IBC de
  salud»*. Se corrige el archivo y el sistema lo vuelve a intentar.

## Por qué es seguro

- **Se tapan los datos personales antes de copiar:** cédula, nombre, correo, teléfono y
  dirección. Claude ve valores, fechas y el formato, nada más.
- **El documento se verifica en el equipo de AZA:** el sistema comprueba que la cédula
  esperada esté en el PDF original; Claude nunca la ve.
- **Claude no decide:** solo transcribe. El estado, el IBC requerido y el correo los calcula
  el sistema con reglas fijas.
- **Queda trazado:** la bitácora marca el caso como «leído por IA».

## Que cada formato se pague una sola vez (TI)

Cuando un formato nuevo se repite, conviene volverlo plantilla:

1. Con un caso ya confirmado, pide al sistema el paquete de plantilla
   (`carril2_asistido.generar_paquete_plantilla`) y pégalo en el mismo proyecto de Claude.
2. Claude responde una plantilla YAML. Guárdala en `plantillas_operador/<operador>.yaml`
   con `estado: borrador`.
3. Pruébala contra la respuesta que ya se confirmó:
   `python -I scripts/probar_plantilla.py plantillas_operador/<operador>.yaml caso.txt respuesta_claude.txt`
4. Si todos los campos coinciden, cambia a `estado: activa` y haz commit. Desde ese momento
   el formato se lee por el carril 1, en segundos y sin Claude.

Para el seguimiento: `salud.json` cuenta cada mes cuántas planillas leyó Claude
(`leidos_por_ia`). Ese número debe bajar mes a mes.
