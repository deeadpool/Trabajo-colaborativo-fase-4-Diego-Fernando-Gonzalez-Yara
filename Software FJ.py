"""
Software FJ - Sistema Integral de Gestión de Clientes, Servicios y Reservas
Universidad Nacional Abierta y a Distancia - Programación (213023)

Características:
  * Programación orientada a objetos (abstracción, herencia, polimorfismo,
    encapsulación).
  * Sin base de datos: todo se maneja con objetos y listas en memoria.
  * Archivos solo para logs de eventos y errores (software_fj.log).
  * Excepciones personalizadas, try/except, try/except/else,
    try/except/finally y encadenamiento (raise ... from ...).

Ejecución:  python software_fj.py
"""

import logging
import re
from abc import ABC, abstractmethod
from enum import Enum
from itertools import count


# =============================================================================
# 1. LOGGING (único uso de archivos)
# =============================================================================
def configurar_logger(ruta="software_fj.log"):
    """Crea un logger que escribe eventos y errores en un archivo."""
    logger = logging.getLogger("SoftwareFJ")
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        manejador = logging.FileHandler(ruta, mode="w", encoding="utf-8")
        manejador.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
        )
        logger.addHandler(manejador)
    return logger


log = configurar_logger()


# =============================================================================
# 2. EXCEPCIONES PERSONALIZADAS
# =============================================================================
class ErrorSoftwareFJ(Exception):
    """Excepción base de toda la aplicación."""


class ErrorValidacion(ErrorSoftwareFJ):
    """Datos inválidos o parámetros faltantes."""


class ClienteInvalidoError(ErrorValidacion):
    """Datos de cliente inválidos."""


class ServicioInvalidoError(ErrorValidacion):
    """Configuración de servicio inválida."""


class ServicioNoDisponibleError(ErrorSoftwareFJ):
    """El servicio existe pero no está disponible."""


class ReservaInvalidaError(ErrorSoftwareFJ):
    """Intento de reserva incorrecto."""


class OperacionNoPermitidaError(ErrorSoftwareFJ):
    """Operación no permitida para el estado actual."""


class CalculoInconsistenteError(ErrorSoftwareFJ):
    """Cálculo de costos con resultado inconsistente."""


# =============================================================================
# 3. CLASE ABSTRACTA DE ENTIDADES GENERALES
# =============================================================================
class EntidadBase(ABC):
    """Entidad general del sistema: todo objeto tiene un id único."""

    _contador = count(1)

    def __init__(self):
        self._id = next(EntidadBase._contador)

    @property
    def id(self):
        return self._id

    @abstractmethod
    def describir(self) -> str:
        """Devuelve una descripción legible de la entidad."""

    def __str__(self):
        return self.describir()


# =============================================================================
# 4. CLIENTE (encapsulación + validaciones robustas)
# =============================================================================
class Cliente(EntidadBase):
    _REGEX_CORREO = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")

    def __init__(self, nombre, documento, correo, telefono):
        super().__init__()
        # Los setters validan; si fallan se encadena la causa original.
        try:
            self.nombre = nombre
            self.documento = documento
            self.correo = correo
            self.telefono = telefono
        except ClienteInvalidoError as error:
            raise ClienteInvalidoError(
                f"No se pudo crear el cliente: {error}"
            ) from error
        self._activo = True

    # --- atributos privados con propiedades ---
    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ClienteInvalidoError("El nombre debe tener al menos 3 caracteres")
        if any(c.isdigit() for c in valor):
            raise ClienteInvalidoError("El nombre no puede contener números")
        self._nombre = valor.strip().title()

    @property
    def documento(self):
        return self._documento

    @documento.setter
    def documento(self, valor):
        valor = str(valor).strip() if valor is not None else ""
        if not valor.isdigit() or not 6 <= len(valor) <= 12:
            raise ClienteInvalidoError("El documento debe tener entre 6 y 12 dígitos")
        self._documento = valor

    @property
    def correo(self):
        return self._correo

    @correo.setter
    def correo(self, valor):
        if not isinstance(valor, str) or not self._REGEX_CORREO.match(valor.strip()):
            raise ClienteInvalidoError(f"Correo inválido: {valor!r}")
        self._correo = valor.strip().lower()

    @property
    def telefono(self):
        return self._telefono

    @telefono.setter
    def telefono(self, valor):
        valor = str(valor).strip() if valor is not None else ""
        if not valor.isdigit() or not 7 <= len(valor) <= 10:
            raise ClienteInvalidoError("El teléfono debe tener entre 7 y 10 dígitos")
        self._telefono = valor

    @property
    def activo(self):
        return self._activo

    def desactivar(self):
        self._activo = False

    def describir(self):
        return f"Cliente #{self.id}: {self.nombre} (doc. {self.documento}, {self.correo})"


# =============================================================================
# 5. SERVICIO ABSTRACTO Y SERVICIOS ESPECIALIZADOS
# =============================================================================
class Servicio(EntidadBase, ABC):
    """Clase abstracta base de todos los servicios de Software FJ."""

    IVA = 0.19

    def __init__(self, nombre, tarifa_hora, disponible=True):
        super().__init__()
        if not isinstance(nombre, str) or not nombre.strip():
            raise ServicioInvalidoError("El servicio requiere un nombre")
        if not isinstance(tarifa_hora, (int, float)) or tarifa_hora <= 0:
            raise ServicioInvalidoError("La tarifa por hora debe ser un número positivo")
        self._nombre = nombre.strip()
        self._tarifa_hora = float(tarifa_hora)
        self._disponible = bool(disponible)

    @property
    def nombre(self):
        return self._nombre

    @property
    def tarifa_hora(self):
        return self._tarifa_hora

    @property
    def disponible(self):
        return self._disponible

    @disponible.setter
    def disponible(self, valor):
        self._disponible = bool(valor)

    # --- métodos abstractos (se sobrescriben en cada servicio) ---
    @abstractmethod
    def calcular_costo_base(self, horas) -> float:
        """Costo sin impuestos ni descuentos."""

    @abstractmethod
    def describir(self) -> str:
        """Descripción del servicio."""

    @abstractmethod
    def validar_parametros(self, horas, **extra) -> None:
        """Valida los parámetros de una reserva para este servicio."""

    # --- validación común ---
    def _validar_horas(self, horas):
        if horas is None:
            raise ErrorValidacion("Falta el parámetro 'horas'")
        if not isinstance(horas, (int, float)) or isinstance(horas, bool):
            raise ErrorValidacion("Las horas deben ser numéricas")
        if not 0 < horas <= 12:
            raise ErrorValidacion("Las horas deben estar entre 0 y 12")

    # --- MÉTODO SOBRECARGADO (variantes por parámetros opcionales) ---
    def calcular_costo(self, horas, impuesto=None, descuento=None) -> float:
        """
        Variantes:
          calcular_costo(h)                  -> costo base
          calcular_costo(h, impuesto)        -> base + impuesto
          calcular_costo(h, impuesto, desc)  -> base - descuento + impuesto
          calcular_costo(h, descuento=desc)  -> base - descuento
        """
        self._validar_horas(horas)
        base = self.calcular_costo_base(horas)
        if base <= 0:
            raise CalculoInconsistenteError(f"Costo base inválido: {base}")
        if descuento is not None:
            if not 0 <= descuento < 1:
                raise CalculoInconsistenteError(
                    f"El descuento debe estar en [0, 1): {descuento}"
                )
            base -= base * descuento
        if impuesto is not None:
            if not 0 <= impuesto <= 1:
                raise CalculoInconsistenteError(
                    f"El impuesto debe estar en [0, 1]: {impuesto}"
                )
            base += base * impuesto
        return round(base, 2)


class ReservaSala(Servicio):
    def __init__(self, nombre, capacidad, tarifa_hora=50_000, disponible=True):
        super().__init__(nombre, tarifa_hora, disponible)
        if not isinstance(capacidad, int) or capacidad <= 0:
            raise ServicioInvalidoError("La capacidad de la sala debe ser un entero positivo")
        self._capacidad = capacidad

    def calcular_costo_base(self, horas):
        total = self.tarifa_hora * horas
        return total * 0.90 if horas >= 4 else total  # 10 % por jornada larga

    def describir(self):
        return (f"Sala '{self.nombre}' - capacidad {self._capacidad} personas, "
                f"${self.tarifa_hora:,.0f}/h")

    def validar_parametros(self, horas, **extra):
        self._validar_horas(horas)
        asistentes = extra.get("asistentes")
        if asistentes is None:
            raise ErrorValidacion("Falta el parámetro 'asistentes' para reservar una sala")
        if not isinstance(asistentes, int) or not 0 < asistentes <= self._capacidad:
            raise ErrorValidacion(
                f"Asistentes inválidos ({asistentes}); capacidad máxima {self._capacidad}"
            )


class AlquilerEquipo(Servicio):
    DEPOSITO = 30_000

    def __init__(self, nombre, stock, tarifa_hora=15_000, disponible=True):
        super().__init__(nombre, tarifa_hora, disponible)
        if not isinstance(stock, int) or stock < 0:
            raise ServicioInvalidoError("El stock debe ser un entero no negativo")
        self._stock = stock

    def calcular_costo_base(self, horas):
        return self.tarifa_hora * horas + self.DEPOSITO

    def describir(self):
        return (f"Equipo '{self.nombre}' - stock {self._stock}, "
                f"${self.tarifa_hora:,.0f}/h + depósito ${self.DEPOSITO:,.0f}")

    def validar_parametros(self, horas, **extra):
        self._validar_horas(horas)
        if self._stock == 0:
            raise ServicioNoDisponibleError(f"Sin stock de '{self.nombre}'")


class Asesoria(Servicio):
    NIVELES = {"junior": 1.0, "senior": 1.5}

    def __init__(self, nombre, especialista, nivel="junior", tarifa_hora=80_000,
                 disponible=True):
        super().__init__(nombre, tarifa_hora, disponible)
        if not isinstance(especialista, str) or not especialista.strip():
            raise ServicioInvalidoError("La asesoría requiere un especialista")
        if nivel not in self.NIVELES:
            raise ServicioInvalidoError(
                f"Nivel inválido '{nivel}'. Opciones: {list(self.NIVELES)}"
            )
        self._especialista = especialista.strip()
        self._nivel = nivel

    def calcular_costo_base(self, horas):
        return self.tarifa_hora * horas * self.NIVELES[self._nivel]

    def describir(self):
        return (f"Asesoría '{self.nombre}' con {self._especialista} "
                f"({self._nivel}), ${self.tarifa_hora:,.0f}/h")

    def validar_parametros(self, horas, **extra):
        self._validar_horas(horas)
        if horas < 1:
            raise ErrorValidacion("Una asesoría dura mínimo 1 hora")


# =============================================================================
# 6. RESERVA
# =============================================================================
class EstadoReserva(Enum):
    PENDIENTE = "Pendiente"
    CONFIRMADA = "Confirmada"
    PROCESADA = "Procesada"
    CANCELADA = "Cancelada"


class Reserva(EntidadBase):
    def __init__(self, cliente, servicio, horas, **parametros):
        super().__init__()
        try:
            if not isinstance(cliente, Cliente):
                raise ReservaInvalidaError("La reserva requiere un Cliente válido")
            if not isinstance(servicio, Servicio):
                raise ReservaInvalidaError("La reserva requiere un Servicio válido")
            servicio.validar_parametros(horas, **parametros)
        except ErrorValidacion as error:
            # Encadenamiento: se conserva la causa original
            raise ReservaInvalidaError(f"Parámetros de reserva inválidos: {error}") from error
        self._cliente = cliente
        self._servicio = servicio
        self._horas = horas
        self._estado = EstadoReserva.PENDIENTE
        self._costo_final = None

    @property
    def estado(self):
        return self._estado

    @property
    def costo_final(self):
        return self._costo_final

    def confirmar(self):
        if self._estado is not EstadoReserva.PENDIENTE:
            raise OperacionNoPermitidaError(
                f"No se puede confirmar una reserva {self._estado.value}"
            )
        if not self._cliente.activo:
            raise OperacionNoPermitidaError("El cliente está inactivo")
        if not self._servicio.disponible:
            raise ServicioNoDisponibleError(f"'{self._servicio.nombre}' no está disponible")
        self._estado = EstadoReserva.CONFIRMADA
        log.info("Reserva #%s confirmada", self.id)

    def cancelar(self):
        if self._estado in (EstadoReserva.PROCESADA, EstadoReserva.CANCELADA):
            raise OperacionNoPermitidaError(
                f"No se puede cancelar una reserva {self._estado.value}"
            )
        self._estado = EstadoReserva.CANCELADA
        log.info("Reserva #%s cancelada", self.id)

    def procesar(self, impuesto=Servicio.IVA, descuento=None):
        """Calcula el costo y cierra la reserva (try/except/else/finally)."""
        resultado = None
        try:
            if self._estado is not EstadoReserva.CONFIRMADA:
                raise OperacionNoPermitidaError(
                    "Solo se procesan reservas confirmadas "
                    f"(estado actual: {self._estado.value})"
                )
            resultado = self._servicio.calcular_costo(self._horas, impuesto, descuento)
        except CalculoInconsistenteError as error:
            raise OperacionNoPermitidaError(
                "No se pudo procesar por un error de cálculo"
            ) from error
        else:
            self._costo_final = resultado
            self._estado = EstadoReserva.PROCESADA
            log.info("Reserva #%s procesada. Total: $%s", self.id, f"{resultado:,.2f}")
        finally:
            log.debug("Fin del procesamiento de la reserva #%s (estado: %s)",
                      self.id, self._estado.value)
        return resultado

    def describir(self):
        costo = f"${self._costo_final:,.2f}" if self._costo_final else "-"
        return (f"Reserva #{self.id} | {self._cliente.nombre} | {self._servicio.nombre} | "
                f"{self._horas} h | {self._estado.value} | Total: {costo}")


# =============================================================================
# 7. GESTOR (listas internas; mantiene la app estable ante cualquier error)
# =============================================================================
class GestorFJ:
    def __init__(self):
        self.clientes, self.servicios, self.reservas = [], [], []

    def _ejecutar(self, etiqueta, funcion, *args, **kwargs):
        """Ejecuta una operación, registra el resultado y nunca deja caer la app."""
        try:
            resultado = funcion(*args, **kwargs)
        except ErrorSoftwareFJ as error:
            causa = f" | causa: {error.__cause__}" if error.__cause__ else ""
            log.error("%s FALLÓ -> %s: %s%s", etiqueta, type(error).__name__, error, causa)
            print(f"   [ERROR CONTROLADO] {type(error).__name__}: {error}")
            return None
        except Exception as error:  # error inesperado: se registra igualmente
            log.critical("%s ERROR INESPERADO -> %r", etiqueta, error)
            print(f"   [ERROR INESPERADO] {error!r}")
            return None
        else:
            log.info("%s OK", etiqueta)
            return resultado
        finally:
            log.debug("Operación finalizada: %s", etiqueta)

    def registrar_cliente(self, *args, **kwargs):
        cliente = self._ejecutar("Registro de cliente", Cliente, *args, **kwargs)
        if cliente:
            self.clientes.append(cliente)
            print(f"   OK -> {cliente}")
        return cliente

    def crear_servicio(self, clase, *args, **kwargs):
        servicio = self._ejecutar(f"Creación de {clase.__name__}", clase, *args, **kwargs)
        if servicio:
            self.servicios.append(servicio)
            print(f"   OK -> {servicio}")
        return servicio

    def crear_reserva(self, cliente, servicio, horas, **parametros):
        reserva = self._ejecutar("Creación de reserva", Reserva,
                                 cliente, servicio, horas, **parametros)
        if reserva:
            self.reservas.append(reserva)
            print(f"   OK -> {reserva}")
        return reserva

    def confirmar_y_procesar(self, reserva, **kwargs):
        if reserva is None:
            print("   (sin reserva que procesar)")
            return None
        if self._ejecutar("Confirmación", reserva.confirmar) is None and \
                reserva.estado is EstadoReserva.PENDIENTE:
            # confirmar() devuelve None si va bien; se revisa el estado real
            return None
        total = self._ejecutar("Procesamiento", reserva.procesar, **kwargs)
        if total is not None:
            print(f"   OK -> {reserva}")
        return total


# =============================================================================
# 8. SIMULACIÓN (mínimo 10 operaciones, válidas e inválidas)
# =============================================================================
def simular():
    g = GestorFJ()
    log.info("=== INICIO DE LA SIMULACIÓN ===")

    print("\n1) Cliente válido")
    ana = g.registrar_cliente("Ana María Pérez", "1098765432", "ana@correo.com", "3001234567")

    print("\n2) Cliente inválido (correo mal formado)")
    g.registrar_cliente("Luis Gómez", "12345678", "luis-correo", "3109876543")

    print("\n3) Cliente inválido (documento con letras)")
    g.registrar_cliente("Carla Ruiz", "ABC123", "carla@correo.com", "3201112233")

    print("\n4) Cliente válido")
    juan = g.registrar_cliente("Juan Torres", "79123456", "juan@correo.com", "3157778899")

    print("\n5) Servicio válido: sala")
    sala = g.crear_servicio(ReservaSala, "Sala Innovación", 10)

    print("\n6) Servicio inválido: tarifa negativa")
    g.crear_servicio(AlquilerEquipo, "Video Beam", 5, tarifa_hora=-100)

    print("\n7) Servicio válido: equipo y asesoría")
    equipo = g.crear_servicio(AlquilerEquipo, "Portátil Gamer", 3)
    asesoria = g.crear_servicio(Asesoria, "Arquitectura de Software", "Dra. Salazar",
                                nivel="senior")

    print("\n8) Reserva exitosa de sala (6 h, 8 asistentes)")
    r1 = g.crear_reserva(ana, sala, 6, asistentes=8)
    g.confirmar_y_procesar(r1)

    print("\n9) Reserva fallida: asistentes exceden la capacidad")
    g.crear_reserva(juan, sala, 3, asistentes=25)

    print("\n10) Reserva fallida: falta parámetro 'asistentes'")
    g.crear_reserva(juan, sala, 2)

    print("\n11) Reserva de equipo con descuento del 10 %")
    r2 = g.crear_reserva(juan, equipo, 5)
    g.confirmar_y_procesar(r2, descuento=0.10)

    print("\n12) Servicio no disponible")
    asesoria.disponible = False
    r3 = g.crear_reserva(ana, asesoria, 2)
    g.confirmar_y_procesar(r3)

    print("\n13) Operación no permitida: cancelar y luego confirmar")
    r4 = g.crear_reserva(ana, equipo, 2)
    if r4:
        r4.cancelar()
        g._ejecutar("Confirmación de reserva cancelada", r4.confirmar)

    print("\n14) Cálculo inconsistente (descuento de 150 %)")
    asesoria.disponible = True
    r5 = g.crear_reserva(juan, asesoria, 3)
    g.confirmar_y_procesar(r5, descuento=1.5)

    print("\n15) Reserva con cliente inexistente (None)")
    g.crear_reserva(None, sala, 2, asistentes=3)

    print("\n--- Demostración de métodos sobrecargados (Asesoría 3 h) ---")
    print(f"   Base:               ${asesoria.calcular_costo(3):,.2f}")
    print(f"   + IVA 19 %:         ${asesoria.calcular_costo(3, 0.19):,.2f}")
    print(f"   + IVA y desc. 10 %: ${asesoria.calcular_costo(3, 0.19, 0.10):,.2f}")
    print(f"   Solo desc. 10 %:    ${asesoria.calcular_costo(3, descuento=0.10):,.2f}")

    print("\n--- Polimorfismo: describir() en cada servicio ---")
    for servicio in g.servicios:
        print("  ", servicio.describir())

    log.info("=== FIN DE LA SIMULACIÓN: la aplicación siguió estable ===")
    print("\nResumen: "
          f"{len(g.clientes)} clientes, {len(g.servicios)} servicios, "
          f"{len(g.reservas)} reservas. Revise 'software_fj.log'.")


if __name__ == "__main__":
    simular()
