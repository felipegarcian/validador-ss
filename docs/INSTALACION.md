# Instalación en la infraestructura de AZA

Estado: plan. La conexión a Office 365 todavía no está programada; este documento define
qué necesita TI y en qué orden. Los pasos de permisos deben verificarse contra la
documentación vigente de Microsoft antes de ejecutarlos.

## Quién se necesita

Una persona, interna o proveedor, con permisos de administrador de aplicaciones en Entra ID,
de Exchange y de SharePoint.

## Paso a paso

1. **Buzón compartido.** Crear o elegir el buzón de seguridad social. Crear las carpetas
   `Procesados` y `Por revisar`.
2. **Biblioteca de SharePoint.** Crear la biblioteca «Seguridad Social» con las carpetas
   `00_Configuracion/` y `01_Entrada/`. Las carpetas por mes las crea el sistema.
3. **Registro de la aplicación.** Registrar la aplicación en Entra ID. Guardar el identificador
   del inquilino, el de la aplicación y su credencial.
4. **Correo, solo ese buzón.** Dar a la aplicación acceso de lectura y escritura únicamente
   sobre el buzón compartido, con el control de acceso por roles para aplicaciones de
   Exchange Online. Referencia: https://learn.microsoft.com/graph/auth-limit-mailbox-access
5. **SharePoint, solo ese sitio.** Dar a la aplicación el permiso `Sites.Selected` y conceder
   lectura y escritura únicamente sobre el sitio de seguridad social.
6. **Motor.** Instalar el motor (ver opciones abajo) y completar `.env` a partir de `.env.example`.
7. **Prueba de humo.** Correr `pytest -q` y `python -m validador.demo` en el equipo de destino.
8. **Modo sombra.** Un mes procesando en paralelo, sin enviar correos, comparando contra lo
   que valida Gestión Humana.
9. **Activación.** Habilitar los borradores y el tablero.

## Dónde corre el motor

| | Azure Functions con temporizador | Equipo Windows con tarea programada |
|---|---|---|
| Requiere | Suscripción de Azure | Un equipo siempre encendido |
| Credenciales | Azure Key Vault | Variables de entorno del equipo |
| Mantenimiento | Bajo | Actualizaciones y reinicios |
| Cuándo elegirla | Ya tienen Azure | No tienen Azure y quieren empezar |

### Instalación en un equipo Windows

```powershell
git clone <url del repositorio> C:\validador-ss
cd C:\validador-ss
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[pdf]"
copy .env.example .env    # completar los valores
pytest -q
```

Después, crear una tarea en el Programador de tareas que ejecute el motor cada 15 minutos
con la cuenta de servicio.

## Tablero

Se entra con la cuenta de correo de la empresa. Roles: Dirección (consulta), Gestión Humana y
Contabilidad (editan y aprueban correos), Administrador (reglas y plantillas). Para enviar los
correos aprobados, la aplicación necesita además permiso de envío desde el buzón compartido.
Propuesta: página de SharePoint con la lista «Correos SS» en la v1 y Power Apps en la v2. El motor
envía los correos aprobados después de verificar que las cifras no cambiaron. Arquitectura,
roles y paso a paso en [TABLERO.md](TABLERO.md).

## Carril 2: Claude

Apagado por defecto. Para encenderlo se necesita una clave de la API de Anthropic y la
aprobación de AZA sobre el envío de documentos. Solo se envía el PDF que ninguna plantilla leyó.
Los usos de Claude en el tablero (resumen del mes y explicación de casos, sin datos personales)
se describen en [TABLERO.md](TABLERO.md), sección 5.

## Lo que la instalación no pide

Acceso a otros buzones, permisos sobre todo SharePoint, ni cuentas personales.

## Lista de verificación

- [ ] El motor lee solo el buzón compartido; un intento sobre otro buzón falla.
- [ ] El motor escribe solo en el sitio de seguridad social.
- [ ] `.env` no está en el repositorio ni en carpetas compartidas.
- [ ] La credencial tiene fecha de vencimiento anotada en el calendario de TI.
- [ ] La demo corre de punta a punta en el equipo de destino.
