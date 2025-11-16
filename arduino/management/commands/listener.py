import time
import serial

from django.core.management.base import BaseCommand
from django.utils import timezone

from arduino.models import SensorReading, SensorZone, IrrigationEvent

from iot.settings import SERIAL_PORT, BAUDRATE, TIMEOUT_SECONDS
from arduino.utils import parse_data_line, get_zone_state_by_name, send_irrigation_command


class Command(BaseCommand):
    help = "Escucha el puerto serie del arduino y guarda las lecturas de sensores en BBDD"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"Iniciando escucha de Arduino en {SERIAL_PORT} a {BAUDRATE} baudios..."))

        try:
            with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT_SECONDS) as ser:
                self.stdout.write(self.style.SUCCESS("PUERTO SERIAL ABIERTO. Esperando datos..."))

                z1 = SensorZone.objects.get_or_create(
                    name = "Z1"
                )
                
                z2 = SensorZone.objects.get_or_create(
                    name = "Z2"
                )


                while True:
                    raw = ser.readline()
                    flag = False

                    if not raw:
                        continue

                    line = raw.decode("utf-8", errors="ignore").strip()
                    self.stdout.write(f"Línea recibida: {line}")

                    if not line.startswith("DATA;"):
                        self.stdout.write(self.style.WARNING("Línea ignorada, no es un dato válido."))
                        continue

                    try:
                        

                        for key, value in parse_data_line(line).items():
                            if key == "Z1_HUM":
                                SensorReading.objects.create(
                                    zone=z1[0],
                                    humidity=value,
                                )
                                
                                self.stdout.write(self.style.SUCCESS(f"Lectura guardada: Zona 1 - Humedad: {value}%"))

                                if z1[0].is_enabled:
                                    action = z1[0].decide_servo_action(humidity=value)
                                    if action != z1[0].last_servo_state:
                                        IrrigationEvent.objects.create(
                                            zone=z1[0],
                                            action=action,
                                        )

                                        flag = True

                                        z1[0].last_servo_state = action
                                        z1[0].last_updated_at = timezone.now()
                                        z1[0].save(update_fields=['last_servo_state', 'last_updated_at'])

                            elif key == "Z2_HUM":
                                SensorReading.objects.create(
                                    zone=z2[0],
                                    humidity=value,
                                )

                                self.stdout.write(self.style.SUCCESS(f"Lectura guardada: Zona 2 - Humedad: {value}%"))

                                if z2[0].is_enabled:
                                    action = z2[0].decide_servo_action(humidity=value)
                                    if action != z2[0].last_servo_state:
                                        IrrigationEvent.objects.create(
                                            zone=z2[0],
                                            action=action,
                                        )

                                        flag = True

                                        z2[0].last_servo_state = action
                                        z2[0].last_updated_at = timezone.now()
                                        z2[0].save(update_fields=['last_servo_state', 'last_updated_at'])
                    
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error al procesar la línea: {e}"))
                    
                    if flag:
                        z1_on = get_zone_state_by_name("Z1")
                        z2_on = get_zone_state_by_name("Z2")

                        try:
                            send_irrigation_command(z1_on=z1_on, z2_on=z2_on)
                            self.stdout.write(self.style.SUCCESS(f"Comando enviado al Arduino: Z1={'ON' if z1_on else 'OFF'}, Z2={'ON' if z2_on else 'OFF'}"))
                        
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Error al enviar comando al Arduino: {e}"))

                    time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("Interrupción por teclado. Cerrando puerto serie..."))
        
        except serial.SerialException as e:
            self.stdout.write(self.style.ERROR(f"Error al abrir el puerto serie: {e}"))


    
