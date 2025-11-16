from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import IrrigationEvent, SensorZone
from .utils import send_irrigation_command, get_zone_state_by_name

@receiver(post_save, sender=IrrigationEvent)
def send_command_to_arduino_on_irrigation_event(sender, instance, created, **kwargs):
    """
    Envía un comando al Arduino cuando se crea un nuevo evento de riego.
    """
    if not created:
        return 
    
    # 1) Actualizar estado de la propia zona.
    zone = instance.zone
    zone.last_servo_state = instance.action
    zone.save(update_fields=['last_servo_state', 'last_updated_at'])

    # 2) Leer el estado actual de cada zona que tiene el arduino
    z1_on = get_zone_state_by_name("Z1")
    z2_on = get_zone_state_by_name("Z2")

    # 3) Enviar comando al Arduino
    try:
        send_irrigation_command(z1_on=z1_on, z2_on=z2_on)
        print(f"Comando enviado al Arduino para zona {zone.name}: {instance.action}")
    
    except Exception as e:
        print(f"Error al enviar comando al Arduino: {e}")
    
