import serial
from iot.settings import SERIAL_PORT, BAUDRATE, TIMEOUT_SECONDS
from arduino.models import SensorZone

def parse_data_line(line:str) -> dict:
    """
    Parsea una linea de datos recibida desde el dispositivo Arduino.
    Convierte el formato: DATA;Z1_RAW=512;Z1_HUM=45.3;Z2_RAW=600;Z2_HUM=50.1
    a un diccionario:
    {
        "Z1_RAW": 512,
        "Z1_HUM": 45.3,
        "Z2_RAW": 600,
        "Z2_HUM": 50.1
    }
    """
    line = line.strip()
    if not line.startswith("DATA;"):
        raise ValueError("Línea de datos inválida, no comienza con 'DATA;'")
    
    partes = line.split(";")[1:]  # Omitir el prefijo "DATA;"
    data = {}
    
    for parte in partes:
        if '=' in parte:
            clave, valor = parte.split("=", 1)
            data[clave] = valor
    
    return {
        "Z1_RAW": int(data["Z1_RAW"]),
        "Z1_HUM": float(data["Z1_HUM"]),
        "Z2_RAW": int(data["Z2_RAW"]),
        "Z2_HUM": float(data["Z2_HUM"]),
    }


def send_irrigation_command(z1_on: bool, z2_on: bool):
    """
    Envía al arduino un comando del tipo:
    RIEGO;Z1=1;Z2=0
    """
    cmd = f"RIEGO;Z1={'1' if z1_on else '0'};Z2={'1' if z2_on else '0'}\n"
    print(f"Enviando comando: {cmd.strip()}")

    with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT_SECONDS) as ser:
        ser.write(cmd.encode('utf-8'))
        ser.flush()


def get_zone_state_by_name(name: str) -> bool:
    """
    Devuelve el estado actual (ON/OFF) de una zona según su last_servo_state.
    Si la zona no existe, asumimos OFF.
    """
    try:
        zone = SensorZone.objects.get(name=name)
    except SensorZone.DoesNotExist:
        return False

    return zone.last_servo_state == "ON"