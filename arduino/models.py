from django.db import models


class SensorZone(models.Model):
    """
    Representa la zona de riego controlada por el Arduino.
    En este proyecto solo usamos Z1.
    """

    ZONE_CHOICES = (
        ("Z1", "Zona 1"),
    )

    name = models.CharField(
        max_length=2,
        choices=ZONE_CHOICES,
        default="Z1",
        unique=True,
        help_text="Identificador de la zona de riego. En este proyecto sólo usamos Z1.",
    )

    humidity_min = models.FloatField(
        null=True,
        blank=True,
        help_text="Humedad mínima (%) antes de encender el riego.",
    )
    humidity_max = models.FloatField(
        null=True,
        blank=True,
        help_text="Humedad máxima (%) a partir de la cual se apaga el riego.",
    )

    # Activa/desactiva la zona: si está en False, nunca se ordena regar
    is_enabled = models.BooleanField(
        default=True,
        help_text="Si está desactivada, el backend no ordenará riego para esta zona.",
    )

    # Borrado lógico
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    SERVO_CHOICES = (
        ("ON", "Encendido"),
        ("OFF", "Apagado"),
    )

    # Último estado decidido por el backend (no por el Arduino)
    last_servo_state = models.CharField(
        max_length=3,
        choices=SERVO_CHOICES,
        default="OFF",
        help_text="Último estado decidido por el backend para el servomotor.",
    )

    last_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Zona: {self.name}"

    # --------------------------
    # LÓGICA DE DECISIÓN DE RIEGO
    # --------------------------

    def decide_servo_state(self, humidity: float) -> str:
        """
        Decide el estado lógico del servomotor basado en la humedad (%).

        Devuelve:
        - 'ON'  -> encender riego
        - 'OFF' -> apagar riego
        - Si no hay umbrales configurados o la zona está deshabilitada,
          mantiene el estado anterior.
        """
        # Si la zona está deshabilitada o sin umbrales, no cambiar el estado
        if (not self.is_enabled or
                self.humidity_min is None or
                self.humidity_max is None):
            return self.last_servo_state

        if humidity < self.humidity_min:
            return "ON"
        elif humidity > self.humidity_max:
            return "OFF"
        else:
            # Dentro del rango -> mantener lo que ya estaba
            return self.last_servo_state

    def build_riego_command(self, state: str) -> str:
        """
        Construye la orden a enviar al Arduino según el protocolo:

        RIEGO;Z1=1  (ON)
        RIEGO;Z1=0  (OFF)
        """
        value = "1" if state == "ON" else "0"
        return f"RIEGO;{self.name}={value}"

    def apply_servo_decision(self, humidity: float):
        """
        Usa decide_servo_state() para decidir, y si hay cambio de estado:
        - Actualiza last_servo_state
        - Crea un IrrigationEvent
        - Devuelve el comando de riego para enviar al Arduino (string)

        Si no hay cambio de estado, devuelve None.
        """
        new_state = self.decide_servo_state(humidity)

        # Si no hay cambio, no registramos evento ni mandamos comando nuevo
        if new_state == self.last_servo_state:
            return None

        # Actualizar estado
        self.last_servo_state = new_state
        self.save(update_fields=["last_servo_state", "last_updated_at"])

        # Registrar evento
        IrrigationEvent.objects.create(
            zone=self,
            action=new_state,
            humidity_at_event=humidity,
        )

        # Devolver comando tipo: RIEGO;Z1=1 / RIEGO;Z1=0
        return self.build_riego_command(new_state)


class SensorReading(models.Model):
    """
    Representa una lectura de humedad tomada por el Arduino para Z1.
    """
    zone = models.ForeignKey(SensorZone, on_delete=models.CASCADE)
    humidity = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # Ordenar por fecha de creación descendente

    def __str__(self):
        return f"Zona {self.zone.name} - Humedad: {self.humidity}%"


class IrrigationEvent(models.Model):
    """
    Representa un evento de riego iniciado o detenido por el sistema.
    """

    ACTION_CHOICES = (
        ("ON", "Encendido"),
        ("OFF", "Apagado"),
    )

    zone = models.ForeignKey(
        SensorZone,
        on_delete=models.CASCADE,
        related_name="irrigation_events",
    )
    action = models.CharField(max_length=3, choices=ACTION_CHOICES)
    humidity_at_event = models.FloatField(
        help_text="Humedad (%) al momento del evento de riego."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.zone.name} - {self.action} @ {self.humidity_at_event}%"
