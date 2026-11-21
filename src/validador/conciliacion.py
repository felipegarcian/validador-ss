"""Une lectura, identificación, reglas y estado del mes. Es el corazón del proceso."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import calendario
from .esquema import Estado, Expectativa, Reglas, Resultado, Soporte
from .lectura import plantillas
from .lectura.claves import identificar
from .reglas import evaluar


@dataclass
class Mes:
    periodo: str  # "AAAA-MM"
    expectativas: dict[str, Expectativa]
    reglas: Reglas = field(default_factory=Reglas)
    validar_documento: bool = True  # False solo con Bases anonimizadas (cédulas de prueba)
    estados: dict[str, Resultado] = field(default_factory=dict)
    soportes: dict[str, list[Soporte]] = field(default_factory=dict)
    recibidos: dict[str, date] = field(default_factory=dict)
    bitacora: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        anio, mes = calendario.mes_siguiente(self.periodo)
        self.fecha_limite = calendario.n_esimo_dia_habil(anio, mes, self.reglas.dia_habil_corte)
        for cedula, exp in self.expectativas.items():
            if self.reglas.ibc_requerido(exp) is None:
                self.estados[cedula] = Resultado(estado=Estado.SIN_HONORARIOS, motivo="Sin honorarios en el mes.")
            else:
                self.estados.setdefault(cedula, Resultado(
                    estado=Estado.ESPERADO, motivo="Sin planilla recibida.",
                    ibc_requerido=self.reglas.ibc_requerido(exp)))

    def _anotar(self, cedula: str | None, evento: str, detalle: str, cuando: date | None) -> None:
        self.bitacora.append({"fecha": str(cuando or date.today()), "cedula": cedula or "",
                              "evento": evento, "detalle": detalle})

    def recibir_texto(self, texto: str, recibido: date | None = None, remitente: str = "",
                      es_ajuste: bool = False) -> tuple[str | None, Resultado]:
        """Procesa el texto de una planilla. Carril 1; si no hay plantilla, revisión manual."""
        soporte = plantillas.leer(texto)
        if soporte is None:
            resultado = Resultado(estado=Estado.REVISION_MANUAL, codigo_error="L-01",
                                  motivo="Ninguna plantilla reconoce este formato.")
            cedula = identificar(remitente, self.expectativas) if remitente else None
            if cedula and self.estados[cedula].estado == Estado.ESPERADO:
                self.estados[cedula] = resultado
            self._anotar(cedula, "LECTURA", resultado.motivo, recibido)
            return cedula, resultado
        return self.recibir(soporte, recibido, remitente, es_ajuste)

    def _quien(self, soporte: Soporte, remitente: str) -> str | None:
        if soporte.cedula in self.expectativas:
            return soporte.cedula
        # Procedimiento 4.2: el nombre de quien envía el correo se cruza con la Base.
        return identificar(remitente, self.expectativas) or identificar(soporte.nombre or "", self.expectativas)

    def recibir(self, soporte: Soporte, recibido: date | None = None, remitente: str = "",
                es_ajuste: bool = False) -> tuple[str | None, Resultado]:
        cedula = self._quien(soporte, remitente)
        esperado = self.expectativas.get(cedula or "")
        previo = self.estados.get(cedula or "")
        ibc_previo = 0
        if esperado and previo and previo.estado == Estado.PENDIENTE_AJUSTE:
            ibc_previo = previo.ibc_pagado or 0  # 4.8: se suma la planilla original y la de ajuste
        evaluado = soporte if self.validar_documento else soporte.model_copy(update={"cedula": None})
        # El indicador cuenta el primer correo recibido.
        primero = self.recibidos.get(cedula or "", recibido)
        resultado = evaluar(evaluado, esperado, self.periodo, self.reglas, primero, self.fecha_limite, ibc_previo)
        if esperado is not None:
            self.estados[esperado.cedula] = resultado
            self.soportes.setdefault(esperado.cedula, []).append(soporte)
            if recibido:
                self.recibidos.setdefault(esperado.cedula, recibido)
        tipo = "Ajuste. " if (es_ajuste or ibc_previo) else ""
        self._anotar(cedula, resultado.estado.value,
                     f"{tipo}{resultado.motivo} Lectura: {soporte.origen_lectura} ({soporte.operador}).", recibido)
        return (esperado.cedula if esperado else None), resultado

    def cerrar_corte(self, hoy: date | None = None) -> list[str]:
        """Al cierre del día de corte, quienes siguen ESPERADO pasan a NO ENVIÓ."""
        pendientes = [c for c, r in self.estados.items() if r.estado == Estado.ESPERADO]
        for cedula in pendientes:
            self.estados[cedula] = Resultado(estado=Estado.NO_ENVIO, motivo="No llegó planilla a la fecha límite.",
                                             ibc_requerido=self.estados[cedula].ibc_requerido)
            self._anotar(cedula, Estado.NO_ENVIO.value, "Corte del plazo.", hoy)
        return pendientes

    def resumen(self) -> dict[str, int]:
        cuenta: dict[str, int] = {}
        for resultado in self.estados.values():
            cuenta[resultado.estado.value] = cuenta.get(resultado.estado.value, 0) + 1
        return cuenta

    def indicador(self) -> dict[str, int | None]:
        return {c: r.indicador for c, r in self.estados.items()}
