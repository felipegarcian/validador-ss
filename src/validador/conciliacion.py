"""Une lectura, reglas y estado del mes. Es el corazón del proceso."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import calendario
from .esquema import Estado, Expectativa, Reglas, Resultado, Soporte
from .lectura import plantillas
from .reglas import evaluar


@dataclass
class Mes:
    periodo: str  # "AAAA-MM"
    expectativas: dict[str, Expectativa]
    reglas: Reglas = field(default_factory=Reglas)
    estados: dict[str, Resultado] = field(default_factory=dict)
    bitacora: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        anio, mes = calendario.mes_siguiente(self.periodo)
        self.fecha_limite = calendario.n_esimo_dia_habil(anio, mes, self.reglas.dia_habil_corte)
        for cedula in self.expectativas:
            self.estados.setdefault(cedula, Resultado(estado=Estado.ESPERADO, motivo="Sin soporte recibido."))

    def _anotar(self, cedula: str | None, evento: str, detalle: str, cuando: date | None) -> None:
        self.bitacora.append({"fecha": str(cuando or date.today()), "cedula": cedula or "",
                              "evento": evento, "detalle": detalle})

    def recibir_texto(self, texto: str, recibido: date | None = None) -> tuple[str | None, Resultado]:
        """Procesa el texto de un comprobante. Carril 1; si no hay plantilla, revisión manual."""
        soporte = plantillas.leer(texto)
        if soporte is None:
            resultado = Resultado(estado=Estado.REVISION_MANUAL, codigo_error="L-01",
                                  motivo="Ninguna plantilla reconoce este formato.")
            self._anotar(None, "LECTURA", resultado.motivo, recibido)
            return None, resultado
        return self.recibir(soporte, recibido)

    def recibir(self, soporte: Soporte, recibido: date | None = None) -> tuple[str | None, Resultado]:
        esperado = self.expectativas.get(soporte.cedula or "")
        resultado = evaluar(soporte, esperado, self.periodo, self.reglas, recibido, self.fecha_limite)
        if esperado is not None:
            self.estados[esperado.cedula] = resultado
        self._anotar(soporte.cedula, resultado.estado.value,
                     f"{resultado.motivo} Lectura: {soporte.origen_lectura}.", recibido)
        return (esperado.cedula if esperado else None), resultado

    def cerrar_corte(self, hoy: date | None = None) -> list[str]:
        """Al cierre del día de corte, quienes siguen ESPERADO pasan a NO ENTREGÓ."""
        pendientes = [c for c, r in self.estados.items() if r.estado == Estado.ESPERADO]
        for cedula in pendientes:
            self.estados[cedula] = Resultado(estado=Estado.NO_ENTREGO, motivo="No entregó antes del corte.")
            self._anotar(cedula, Estado.NO_ENTREGO.value, "Corte del plazo.", hoy)
        return pendientes

    def resumen(self) -> dict[str, int]:
        cuenta: dict[str, int] = {}
        for resultado in self.estados.values():
            cuenta[resultado.estado.value] = cuenta.get(resultado.estado.value, 0) + 1
        return cuenta
