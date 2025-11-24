import time
import serial
from iot.settings import SERIAL_PORT, BAUDRATE, TIMEOUT_SECONDS
from typing import Optional

def send_command(ser: serial.Serial, command:str) -> None:
    """
    Envía un comando al Arduino a través del puerto serie.
    """
    line = f"{command}\n"
    ser.write(line.encode('utf-8'))
    ser.flush()
    time.sleep(0.1)  # Pequeña pausa para asegurar el envío

def irrigation_on(ser: serial.Serial) -> None:
    """
    Envía el comando para activar el riego.
    """
    send_command(ser, "RIEGO;1")

def irrigation_off(ser: serial.Serial) -> None:
    """
    Envía el comando para desactivar el riego.
    """
    send_command(ser, "RIEGO;0")

def parse_data_line(line: str) -> dict[str, float]:
    """
    A partir de una línea del tipo:
        DATA;HUM=45.2;RAW=678

    Devuelve un objeto SensorReading con los valores parseados.
    Si la línea no es válida, lanza una excepción ValueError.
    """
    # Normalizamos la línea
    if line is None:
        raise ValueError("Línea de datos nula")

    line = line.strip()
    if not line:
        raise ValueError("Línea de datos vacía")

    # Debe comenzar con "DATA;"
    if not line.startswith("DATA;"):
        raise ValueError("Línea de datos inválida, no comienza con 'DATA;'")

    # Intentamos separar el prefijo "DATA;" del resto
    try:
        _, payload = line.split(";", 1)
    except ValueError:
        # No hay nada después de "DATA;"
        raise ValueError("Línea de datos inválida, falta payload después de 'DATA;'")

    data: dict[str, float] = {}

    for part in payload.split(";"):
        part = part.strip()
        if not part:
            continue

        if "=" not in part:
            # Parte sin "=", la ignoramos
            continue

        key, value_str = part.split("=", 1)
        key = key.strip()
        value_str = value_str.strip()

        if not key:
            # Clave vacía, ignoramos
            continue

        try:
            value = float(value_str)
        except ValueError:
            # Valor no numérico, ignoramos
            continue

        data[key] = value

    return data

def open_serial_port() -> serial.Serial:
    """
    Abre y devuelve el puerto serie configurado para comunicarse con el Arduino.
    Puede lanzar serial.SerialException si no se puede abrir.
    """
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUDRATE,
        timeout=TIMEOUT_SECONDS,
    )
    return ser

def close_serial_port(ser: serial.Serial) -> None:
    """
    Cierra el puerto serie si está abierto.
    """
    if ser and ser.is_open:
        ser.close()

def read_line_from_serial(ser: serial.Serial) -> Optional[str]:
    """
    Lee una línea del puerto serie.
    Devuelve la línea como string, o None si no se pudo leer nada
    o si ocurre un error.
    """
    try:
        line_bytes = ser.readline()
        if not line_bytes:
            return None

        # Ignoramos errores de decodificación por si llega algún byte raro
        line = line_bytes.decode("utf-8", errors="ignore").strip()
        return line or None
    except (serial.SerialException, OSError, UnicodeDecodeError):
        return None

