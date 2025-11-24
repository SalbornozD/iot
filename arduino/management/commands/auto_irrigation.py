import time
import serial

from django.core.management.base import BaseCommand

from arduino.models import Flowerpot, SensorReading
from arduino.utils import (
    open_serial_port,
    close_serial_port,
    read_line_from_serial,
    parse_data_line,
    send_command,
)

# Cantidad de lecturas instantáneas que se promedian
NUM_SAMPLES_FOR_AVG = 10

# Pausa entre intentos de lectura (para no saturar CPU)
READ_SLEEP_SECONDS = 0.1


class Command(BaseCommand):
    help = (
        "Lee continuamente la humedad enviada por el Arduino, decide riego "
        "según la lógica manual/automática de la maceta y guarda lecturas promediadas."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                "Iniciando riego automático: lectura continua de Arduino..."
            )
        )

        # Obtenemos la maceta que se va a controlar con este Arduino.
        # Aquí asumo que usas una sola maceta; ajusta si necesitas varias.
        flowerpot = Flowerpot.objects.select_related("plant").first()

        if not flowerpot:
            self.stdout.write(
                self.style.ERROR(
                    "No se encontró ninguna maceta (Flowerpot) en la base de datos. "
                    "Crea al menos una para poder usar este comando."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Maceta obtenida: {flowerpot} | "
                f"manual_irrigation={flowerpot.manual_irrigation} | "
                f"automatic_irrigation={flowerpot.automatic_irrigation} | "
                f"last_servo_state={flowerpot.last_servo_state}"
            )
        )

        # Buffer para promediar humedad
        buffer_hum = []

        try:
            # Abrimos el puerto serie
            try:
                ser = open_serial_port()
            except serial.SerialException as e:
                self.stdout.write(
                    self.style.ERROR(f"No se pudo abrir el puerto serie: {e}")
                )
                return

            self.stdout.write(
                self.style.SUCCESS("Puerto serie abierto. Esperando datos 'DATA;...'")
            )

            # Bucle principal
            while True:
                line = read_line_from_serial(ser)

                # Siempre mostramos la línea leída (aunque sea None)
                self.stdout.write(f"[DEBUG] Línea leída del serial: {line!r}")

                if line is None:
                    # Nada nuevo, esperamos un poco
                    time.sleep(READ_SLEEP_SECONDS)
                    continue

                # Validamos prefijo
                if not line.startswith("DATA;"):
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DEBUG] Línea ignorada (no comienza con 'DATA;'): {line!r}"
                        )
                    )
                    continue

                # Parseamos con el helper
                try:
                    data = parse_data_line(line)
                except ValueError as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Línea de datos inválida, se ignora: {line} ({e})"
                        )
                    )
                    continue

                self.stdout.write(f"[DEBUG] Dict parseado: {data}")

                # Buscamos la clave de humedad (solo HUM)
                humidity_value = data.get("HUM")

                if humidity_value is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Línea sin campo de humedad esperado (HUM), se ignora: {line}"
                        )
                    )
                    continue

                # Aseguramos float
                try:
                    humidity = float(humidity_value)
                except (TypeError, ValueError):
                    self.stdout.write(
                        self.style.WARNING(
                            f"Valor de humedad no numérico, se ignora: {humidity_value!r}"
                        )
                    )
                    continue

                self.stdout.write(
                    f"[DEBUG] Humedad instantánea leída: {humidity:.2f}%"
                )

                # Refrescamos la maceta desde la BBDD por si cambió manual/automático
                flowerpot.refresh_from_db()

                self.stdout.write(
                    "[DEBUG] Estado actual en BD -> "
                    f"manual_irrigation={flowerpot.manual_irrigation}, "
                    f"automatic_irrigation={flowerpot.automatic_irrigation}, "
                    f"last_servo_state={flowerpot.last_servo_state}"
                )

                # ----------------------------------------
                # LÓGICA DE RIEGO:
                # - Si manual_irrigation = True -> abre la llave (ON)
                # - Si manual_irrigation = False y automatic_irrigation = True:
                #       usa humidity_min / humidity_max de la planta
                # - Si manual_irrigation = False y automatic_irrigation = False:
                #       OFF
                # Toda esa lógica está en Flowerpot.decide_servo_state()
                # y se aplica aquí con apply_servo_decision().
                # ----------------------------------------
                command = flowerpot.apply_servo_decision(humidity)

                self.stdout.write(
                    f"[DEBUG] Nuevo last_servo_state en BD: {flowerpot.last_servo_state}"
                )

                if command:
                    mode_label = "[MANUAL]" if flowerpot.manual_irrigation else "[AUTO]"

                    self.stdout.write(
                        f"[DEBUG] Comando generado para Arduino: {command}"
                    )

                    try:
                        send_command(ser, command)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"{mode_label} Comando de riego enviado al Arduino: {command}"
                            )
                        )
                    except serial.SerialException as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Error al enviar comando de riego al Arduino: {e}"
                            )
                        )
                else:
                    self.stdout.write(
                        "[DEBUG] Sin cambio de estado del servo; no se envía comando."
                    )

                # -------------------------
                # PROMEDIO CADA X LECTURAS
                # -------------------------
                buffer_hum.append(humidity)

                self.stdout.write(
                    f"[DEBUG] Buffer de humedades ({len(buffer_hum)} muestras): {buffer_hum}"
                )

                # Cuando llegamos a NUM_SAMPLES_FOR_AVG, calculamos promedio
                if len(buffer_hum) >= NUM_SAMPLES_FOR_AVG:
                    avg_humidity = sum(buffer_hum) / len(buffer_hum)

                    # Guardamos una única lectura promedio
                    SensorReading.objects.create(
                        flowerpot=flowerpot,
                        humidity=avg_humidity,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[Maceta {flowerpot.id}] Lectura promedio guardada "
                            f"({len(buffer_hum)} muestras): {avg_humidity:.2f}%"
                        )
                    )

                    # Reiniciamos el buffer
                    buffer_hum.clear()

                # Pequeña pausa para no saturar CPU
                time.sleep(READ_SLEEP_SECONDS)

        except KeyboardInterrupt:
            self.stdout.write(
                self.style.SUCCESS(
                    "Interrupción por teclado (Ctrl+C). Cerrando riego automático..."
                )
            )
        finally:
            # Cerrar siempre el puerto serie si lo abrimos
            try:
                close_serial_port(ser)
                self.stdout.write(self.style.SUCCESS("Puerto serie cerrado."))
            except Exception:
                # Por si ser no existe o ya está cerrado
                pass
