Suposiciones de Hardware

Zona 1: 
- Sensor de humedad: AO -> A0
- Servomotor: D9

Zona 2:
- Sensor de humedad: AO -> A1
- Servomotor: D10

Protocolo Serial Arduino <-> Django.

Arduino -> Django (Envio de datos).

Cada cierto intervalo (ej. 2 segundos) el Arduino envía una línea de texto.
DATA;Z1_RAW=512;Z1_HUM=43.21;Z2_RAW=623;Z2_HUM=35.67

DATA -> Indica el comienzo de la lectura
Z1_RAW -> Valor "crudo" del Sensor Z1
Z1_HUM -> Humedad estimada del Sensor Z1
Z2_RAW -> Valor "crudo" del Sensor Z2
Z2_HUM -> Humedad estimada del Sensor Z2 

Z1 y Z2 son las zonas (o las macetas)

Django -> Arduino

RIEGO;Z1=1;Z2=0

0 -> No Riego
1 -> Riego
