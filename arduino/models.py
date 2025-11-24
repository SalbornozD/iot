from django.conf import settings
from django.db import models
from typing import Optional


class PlantCategory(models.Model):
    """Categoría de planta (por ejemplo: interior, suculenta, árbol)."""

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre de la categoría",
        help_text="Nombre de la categoría (por ejemplo: interior, suculenta).",
    )

    def __str__(self) -> str:
        return self.name


class Plants(models.Model):
    name = models.CharField(  # Nombre de la planta
        max_length=255,
        verbose_name="Nombre de la planta",
        help_text="Nombre común de la planta."
    )

    # URL de la imagen remota para facilitar su uso desde Flutter
    image_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="URL de la imagen",
        help_text="URL pública de la imagen de la planta."
    )

    # Una planta puede pertenecer a varias categorías (interior, suculenta, árbol, etc.)
    categories = models.ManyToManyField(
        PlantCategory,
        related_name="plants",
        blank=True,
        verbose_name="Categorías",
        help_text="Categorías asociadas a la planta (interior, suculenta, árbol, etc.).",
    )

    humidity_min = models.FloatField(  # Umbral mínimo de humedad
        default=20.0,
        verbose_name="Humedad mínima (%)",
        help_text="Humedad mínima (%) antes de activar el riego."
    )

    humidity_max = models.FloatField(  # Umbral máximo de humedad
        default=60.0,
        verbose_name="Humedad máxima (%)",
        help_text="Humedad máxima (%) a partir de la cual se apaga el riego."
    )

    created_at = models.DateTimeField(  # Fecha de creación
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )

    def __str__(self):
        return f"Planta: {self.name}"


class Flowerpot(models.Model):
    SERVO_CHOICES = (
        ("ON", "Encendido"),
        ("OFF", "Apagado"),
    )

    plant = models.ForeignKey(
        Plants,
        on_delete=models.CASCADE,
        verbose_name="Planta asociada",
        related_name="flowerpots",
    )

    manual_irrigation = models.BooleanField(
        default=False,
        verbose_name="Riego manual",
        help_text="Si está activo, el riego se mantiene siempre encendido."
    )

    automatic_irrigation = models.BooleanField(
        default=True,
        verbose_name="Riego automático",
        help_text="Si está activo, el riego se decide según la humedad."
    )

    last_servo_state = models.CharField(
        max_length=3,
        choices=SERVO_CHOICES,
        default="OFF",
        help_text="Último estado decidido para el servomotor.",
    )

    last_updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )

    def __str__(self):
        return f"Maceta de {self.plant.name} (ID: {self.id})"

    # --------------------------
    # LÓGICA DE DECISIÓN DE RIEGO
    # --------------------------

    def decide_servo_state(self, humidity: float) -> str:
        """
        Devuelve 'ON' o 'OFF' según las siguientes reglas:

        1) Si manual_irrigation == True  -> 'ON'
        2) Si manual_irrigation == False y automatic_irrigation == False -> 'OFF'
        3) Si manual_irrigation == False y automatic_irrigation == True:
           - Si humedad < humidity_min -> 'ON'
           - Si humedad > humidity_max -> 'OFF'
           - Si está entre min y max   -> se mantiene el último estado
        """

        # 1) PRIORIDAD: MODO MANUAL
        if self.manual_irrigation:
            return "ON"

        # 2) SIN MANUAL Y SIN AUTOMÁTICO -> SIEMPRE APAGADO
        if not self.automatic_irrigation:
            return "OFF"

        # 3) MODO AUTOMÁTICO: usar rangos de humedad de la planta
        if (
            self.plant is None or
            self.plant.humidity_min is None or
            self.plant.humidity_max is None
        ):
            # Si falta info de la planta, por seguridad apagamos
            return "OFF"

        if humidity < self.plant.humidity_min:
            return "ON"
        elif humidity > self.plant.humidity_max:
            return "OFF"
        else:
            # Dentro del rango, mantenemos como estaba para evitar cambios constantes
            return self.last_servo_state

    def build_riego_command(self, state: str) -> str:
        """
        RIEGO;1  -> encender
        RIEGO;0  -> apagar
        """
        value = "1" if state == "ON" else "0"
        return f"RIEGO;{value}"

    def apply_servo_decision(self, humidity: float) -> Optional[str]:
        """
        Calcula el nuevo estado con decide_servo_state() y, si cambia:
        - Actualiza last_servo_state
        - Crea un IrrigationEvent (marcando si fue manual o automático)
        - Devuelve el comando a enviar al Arduino (RIEGO;1 / RIEGO;0)

        Si no hay cambio de estado, devuelve None.
        """
        new_state = self.decide_servo_state(humidity)

        if new_state == self.last_servo_state:
            return None

        # Actualizar estado en BD
        self.last_servo_state = new_state
        self.save(update_fields=["last_servo_state", "last_updated_at"])

        # Determinar si este evento fue manual o automático
        irrigation_mode = "MANUAL" if self.manual_irrigation else "AUTO"

        # Registrar evento
        IrrigationEvent.objects.create(
            flowerpot=self,
            action=new_state,
            humidity_at_event=humidity,
            mode=irrigation_mode,
        )

        # Comando para el Arduino
        return self.build_riego_command(new_state)


class SensorReading(models.Model):
    """
    Representa una lectura de humedad tomada por el Arduino para el macetero.
    """
    flowerpot = models.ForeignKey(  # Macetero asociado
        Flowerpot,
        on_delete=models.CASCADE,
        related_name="sensor_readings",
        verbose_name="Macetero",
    )

    humidity = models.FloatField(  # Humedad (%)
        help_text="Humedad medida por el sensor (%).",
        verbose_name="Humedad (%)"
    )

    created_at = models.DateTimeField(  # Fecha de creación
        auto_now_add=True,
        verbose_name="Fecha de lectura"
    )

    class Meta:
        ordering = ["-created_at"]  # Ordenar por fecha de creación descendente

    def __str__(self):
        return f"Maceta {self.flowerpot.id} - Humedad: {self.humidity}%"


class IrrigationEvent(models.Model):
    """
    Representa un evento de riego iniciado o detenido por el sistema.
    """

    ACTION_CHOICES = (  # Tipos de acción
        ("ON", "Encendido"),
        ("OFF", "Apagado"),
    )

    MODE_CHOICES = (  # Modo de riego
        ("MANUAL", "Manual"),
        ("AUTO", "Automático"),
    )

    flowerpot = models.ForeignKey(  # Macetero asociado
        Flowerpot,
        on_delete=models.CASCADE,
        related_name="irrigation_events",
        verbose_name="Macetero",
    )

    action = models.CharField(  # Acción realizada
        max_length=3,
        choices=ACTION_CHOICES,
        verbose_name="Acción",
    )

    mode = models.CharField(  # Modo de riego (manual/automático)
        max_length=7,
        choices=MODE_CHOICES,
        verbose_name="Modo de riego",
        help_text="Indica si el riego fue manual o automático.",
    )

    humidity_at_event = models.FloatField(  # Humedad (%) al momento del evento de riego
        help_text="Humedad (%) al momento del evento de riego.",
        verbose_name="Humedad (%) al evento"
    )

    created_at = models.DateTimeField(  # Fecha de creación
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Maceta {self.flowerpot.id} - {self.action} "
            f"({self.mode}) @ {self.humidity_at_event}%"
        )
