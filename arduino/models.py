from django.db import models


class SensorZone(models.Model):
    """
    Representa una zona de sensores asociada a un dispositivo Arduino.
    """
    name = models.CharField(max_length=2)
    
    humidity_min = models.FloatField(null=True, blank=True)
    humidity_max = models.FloatField(null=True, blank=True)

    is_enabled = models.BooleanField(default=True) # Activa desactiva la zona, es decir no se riega aunque lleguen lecturas.
    
    is_active = models.BooleanField(default=True) # Borrado lógico del registro
    created_at = models.DateTimeField(auto_now_add=True) 

    last_servo_state = models.CharField(
        max_length=3,
        choices=(("ON", "Encendido"), ("OFF", "Apagado")),
        default="OFF",
    ) # Ultimo estado decido por el backend. ON (regando) OFF (no regando)

    last_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Zona: {self.name}"
    
    def decide_servo_action(self, humidity: float) -> str:
        """
        Decide la acción del servomotor basado en la humedad registrada.
        """
        if humidity < self.humidity_min:
            return "ON"  # Activar riego
        
        elif humidity > self.humidity_max:
            return "OFF"  # Desactivar riego
        
        else: 
            return self.last_servo_state  # Mantener el estado actual

class SensorReading(models.Model):
    """
    Representa una lectura de sensor de humedad tomada por un dispositivo Arduino.
    """
    zone = models.ForeignKey(SensorZone, on_delete=models.CASCADE)
    humidity = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # Ordenar por fecha de creación descendente

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

    zone = models.ForeignKey(SensorZone, on_delete=models.CASCADE, related_name='irrigation_events')
    action = models.CharField(max_length=3, choices=ACTION_CHOICES)
    humidity_at_event = models.FloatField()  # Humedad registrada al momento del evento
    created_at = models.DateTimeField(auto_now_add=True)
