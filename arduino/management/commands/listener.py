import time
import serial

from django.core.management.base import BaseCommand

from arduino.models import SensorReading, SensorZone
from iot.settings import SERIAL_PORT, BAUDRATE, TIMEOUT_SECONDS
from arduino.utils import parse_data_line  # seguimos reutilizando tu parser

# Segundos de la ventana para promediar lecturas (para guardar en BBDD)
AGGREGATION_WINDOW_SECONDS = 60  # cambia a 10, 30, etc. si quieres

# Activa / desactiva logs de debug
DEBUG = False


class Command(BaseCommand):
    help = (
        "Escucha el puerto serie del Arduino, decide riego en cada lectura "
        "y guarda lecturas de humedad promediadas (1 registro por minuto, solo Z1)."
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f"Iniciando escucha de Arduino en {SERIAL_PORT} a {BAUDRATE} baudios..."
            )
        )

        try:
            with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT_SECONDS) as ser:
                self.stdout.write(
                    self.style.SUCCESS("PUERTO SERIAL ABIERTO. Esperando datos...")
                )

                # Nos aseguramos que exista la zona Z1
                zone, created = SensorZone.objects.get_or_create(name="Z1")
                if DEBUG:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[DEBUG] Zona obtenida: {zone} (creada={created}) | "
                            f"last_servo_state={zone.last_servo_state}"
                        )
                    )

                # Buffer para promediar lecturas (para la BBDD)
                buffer_hum = []
                window_start = time.monotonic()

                while True:
                    raw = ser.readline()

                    if DEBUG:
                        self.stdout.write(
                            self.style.HTTP_INFO(f"[DEBUG] raw leído: {raw!r}")
                        )

                    if not raw:
                        # Nada nuevo por el puerto serie
                        time.sleep(0.1)
                        continue

                    line = raw.decode("utf-8", errors="ignore").strip()

                    if DEBUG:
                        self.stdout.write(
                            self.style.HTTP_INFO(f"[DEBUG] línea decodificada: '{line}'")
                        )

                    if not line.startswith("DATA;"):
                        self.stdout.write(
                            self.style.WARNING(
                                f"Línea ignorada (no comienza con DATA;): {line}"
                            )
                        )
                        continue

                    try:
                        data = parse_data_line(line)

                        if DEBUG:
                            self.stdout.write(
                                self.style.HTTP_INFO(
                                    f"[DEBUG] Dict parseado: {data}"
                                )
                            )

                        # Esperamos algo como: DATA;Z1_RAW=1023;Z1_HUM=0.00
                        humidity = data.get("Z1_HUM", None)

                        if humidity is None:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Línea sin Z1_HUM, se ignora: {line}"
                                )
                            )
                            continue

                        # Aseguramos float
                        humidity = float(humidity)

                        # ---- LÓGICA 1: CONTROL DEL MOTOR (en cada lectura) ----
                        # Aquí reaccionamos inmediatamente a la humedad actual
                        if DEBUG:
                            self.stdout.write(
                                self.style.HTTP_INFO(
                                    f"[DEBUG] Humedad instantánea: {humidity:.2f}% -> "
                                    "llamando a zone.apply_servo_decision(...)"
                                )
                            )

                        command = zone.apply_servo_decision(humidity)
                        # apply_servo_decision:
                        # - decide ON/OFF
                        # - actualiza last_servo_state
                        # - crea IrrigationEvent si hay cambio
                        # - devuelve algo como "RIEGO;Z1=1" o None

                        if command:
                            if DEBUG:
                                self.stdout.write(
                                    self.style.HTTP_INFO(
                                        f"[DEBUG] Comando generado: {command}"
                                    )
                                )
                            try:
                                ser.write((command + "\n").encode("utf-8"))
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"Comando de riego enviado: {command}"
                                    )
                                )
                            except Exception as e:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"Error al enviar comando al Arduino: {e}"
                                    )
                                )
                        else:
                            if DEBUG:
                                self.stdout.write(
                                    self.style.HTTP_INFO(
                                        "[DEBUG] Sin cambio de estado del servo, "
                                        "no se envía comando."
                                    )
                                )

                        # ---- LÓGICA 2: REGISTRO EN BBDD (promedio por minuto) ----
                        buffer_hum.append(humidity)

                        if DEBUG:
                            self.stdout.write(
                                self.style.HTTP_INFO(
                                    f"[DEBUG] Añadida al buffer para promedio: {humidity:.2f}% | "
                                    f"Buffer actual ({len(buffer_hum)} muestras): {buffer_hum}"
                                )
                            )

                        now = time.monotonic()
                        elapsed = now - window_start

                        if DEBUG:
                            self.stdout.write(
                                self.style.HTTP_INFO(
                                    f"[DEBUG] Tiempo en ventana: {elapsed:.1f}s / "
                                    f"objetivo={AGGREGATION_WINDOW_SECONDS}s"
                                )
                            )

                        # ¿Se completó la ventana de agregación?
                        if elapsed >= AGGREGATION_WINDOW_SECONDS and buffer_hum:
                            avg_humidity = sum(buffer_hum) / len(buffer_hum)

                            # Guardamos SOLO una lectura promedio por ventana
                            SensorReading.objects.create(
                                zone=zone,
                                humidity=avg_humidity,
                            )
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"[Z1] Lectura promedio guardada "
                                    f"({len(buffer_hum)} muestras): {avg_humidity:.2f}%"
                                )
                            )

                            # Reiniciar ventana (sin tocar el servo, ya se maneja por lectura)
                            buffer_hum.clear()
                            window_start = now

                            if DEBUG:
                                self.stdout.write(
                                    self.style.HTTP_INFO(
                                        "[DEBUG] Ventana de agregación reiniciada."
                                    )
                                )

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error al procesar la línea '{line}': {e}")
                        )

                    time.sleep(0.1)

        except KeyboardInterrupt:
            self.stdout.write(
                self.style.SUCCESS("Interrupción por teclado. Cerrando puerto serie...")
            )

        except serial.SerialException as e:
            self.stdout.write(
                self.style.ERROR(f"Error al abrir el puerto serie: {e}")
            )
