import serial
from iot.settings import SERIAL_PORT, BAUDRATE, TIMEOUT_SECONDS
from arduino.models import SensorZone

def parse_data_line(line: str) -> dict:
    """
    Parsea una línea tipo:
        DATA;Z1_RAW=1023;Z1_HUM=0.00

    Devuelve un dict como:
        {
            "Z1_RAW": 1023.0,
            "Z1_HUM": 0.0,
        }

    Es genérica: si algún campo no viene, simplemente no aparece en el dict.
    """
    line = line.strip()

    if not line.startswith("DATA;"):
        raise ValueError("Línea de datos inválida, no comienza con 'DATA;'")

    # Quitamos el prefijo "DATA;" y tomamos el resto
    payload = line.split(";", 1)[1]

    data: dict[str, float] = {}

    for part in payload.split(";"):
        part = part.strip()
        if not part:
            continue

        if "=" not in part:
            # Algo raro sin "=" -> lo ignoramos
            continue

        key, value_str = part.split("=", 1)
        key = key.strip()
        value_str = value_str.strip()

        if not key:
            continue

        try:
            value = float(value_str)
        except ValueError:
            # Si no se puede convertir a float, lo ignoramos
            continue

        data[key] = value

    return data



def send_irrigation_command(z1_on: bool, z2_on: bool, ser:None):
    """
    Envía al arduino un comando del tipo:
    RIEGO;Z1=1;Z2=0
    """
    cmd = f"RIEGO;Z1={'1' if z1_on else '0'};Z2={'1' if z2_on else '0'}\n"
    print(f"Enviando comando: {cmd.strip()}")

    if ser is not None:
        ser.write(cmd.encode('utf-8'))
        ser.flush()
    else:
        with serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT_SECONDS) as s:
            s.write(cmd.encode('utf-8'))
            s.flush()


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