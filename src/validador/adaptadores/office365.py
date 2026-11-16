"""Adaptadores de Office 365 (Microsoft Graph). PENDIENTE DE IMPLEMENTAR.

El núcleo no conoce Office 365: solo recibe textos de soportes y una liquidación.
Estos adaptadores traen y llevan los archivos. Ver docs/INSTALACION.md para los permisos.

Funciones previstas:
- correos_nuevos(buzon): correos con asunto "seguridad social" y su adjunto PDF.
- mover_correo(id, carpeta): a Procesados o Por revisar.
- guardar_borrador(buzon, hilo, asunto, cuerpo): deja la respuesta lista; no envía.
- liquidacion_nueva(sitio): detecta el Excel en 01_Entrada/.
- guardar_soporte(sitio, periodo, cedula, pdf): en AAAA-MM/Soportes/.
- escribir_maestro(sitio, periodo, libro): actualiza Control_SS_AAAA-MM.xlsx.

Variables de entorno: TENANT_ID, CLIENT_ID, CLIENT_SECRET, BUZON, SITIO_SHAREPOINT.
"""
from __future__ import annotations


def correos_nuevos(buzon: str):
    raise NotImplementedError("Conexión a Office 365 pendiente; usar adaptadores.local en la demo.")
