#include <Servo.h>

// ============================
// Configuración de pines
// ============================

// Sensores de humedad
const int PIN_SENSOR_Z1 = A0;
const int PIN_SENSOR_Z2 = A1;

// Servos
const int PIN_SERVO_Z1 = 9;
const int PIN_SERVO_Z2 = 10;

// Ángulos de los servos
const int SERVO_ANGULO_ABIERTO  = 0;    // riego activado (llave abierta)
const int SERVO_ANGULO_CERRADO = 180;  // riego desactivado (llave cerrada)

// Calibración de humedad (AJUSTAR con tus lecturas)
int Z1_VALOR_SECO   = 800;   // lectura con tierra seca para Z1
int Z1_VALOR_MOJADO = 300;   // lectura con tierra muy húmeda/agua para Z1

int Z2_VALOR_SECO   = 800;   // lectura con tierra seca para Z2
int Z2_VALOR_MOJADO = 300;   // lectura con tierra muy húmeda/agua para Z2

// Envío de datos cada X ms
const unsigned long INTERVALO_ENVIO = 2000; // 2 segundos
unsigned long ultimoEnvio = 0;

// Estado de riego (decidido por Django)
bool riegoZ1 = false;
bool riegoZ2 = false;

// Objetos Servo
Servo servoZ1;
Servo servoZ2;

// ============================
// Funciones auxiliares
// ============================

float calcularHumedad(int lectura, int valorSeco, int valorMojado) {
  // Mientras más húmedo, más BAJO es el valor analógico
  float humedad = map(lectura, valorSeco, valorMojado, 0, 100);
  if (humedad < 0)   humedad = 0;
  if (humedad > 100) humedad = 100;
  return humedad;
}

void aplicarEstadoRiego() {
  // Si riego activado -> servo a ángulo de "abierto"
  // Si riego desactivado -> servo a ángulo de "cerrado"
  servoZ1.write(riegoZ1 ? SERVO_ANGULO_ABIERTO : SERVO_ANGULO_CERRADO);
  servoZ2.write(riegoZ2 ? SERVO_ANGULO_ABIERTO : SERVO_ANGULO_CERRADO);
}

// Procesa una línea de comando proveniente de Django
// Formato esperado: RIEGO;Z1=1;Z2=0
void procesarComando(String linea) {
  linea.trim();
  if (!linea.startsWith("RIEGO;")) {
    // No es un comando de riego, ignorar
    return;
  }

  // Buscar Z1=
  int idxZ1 = linea.indexOf("Z1=");
  if (idxZ1 >= 0 && idxZ1 + 3 < (int)linea.length()) {
    char c = linea.charAt(idxZ1 + 3);
    if (c == '1') {
      riegoZ1 = true;
    } else if (c == '0') {
      riegoZ1 = false;
    }
  }

  // Buscar Z2=
  int idxZ2 = linea.indexOf("Z2=");
  if (idxZ2 >= 0 && idxZ2 + 3 < (int)linea.length()) {
    char c = linea.charAt(idxZ2 + 3);
    if (c == '1') {
      riegoZ2 = true;
    } else if (c == '0') {
      riegoZ2 = false;
    }
  }

  aplicarEstadoRiego();

  // (Opcional) Confirmación al PC/Django
  Serial.print("ACK;");
  Serial.print("Z1=");
  Serial.print(riegoZ1 ? 1 : 0);
  Serial.print(";Z2=");
  Serial.println(riegoZ2 ? 1 : 0);
}

// ============================
// Setup y loop principal
// ============================

void setup() {
  Serial.begin(9600);

  servoZ1.attach(PIN_SERVO_Z1);
  servoZ2.attach(PIN_SERVO_Z2);

  // Estado inicial: riego apagado (llaves cerradas)
  riegoZ1 = false;
  riegoZ2 = false;
  aplicarEstadoRiego();
}

void loop() {
  // 1) Leer comandos desde Django (si los hay)
  if (Serial.available() > 0) {
    String linea = Serial.readStringUntil('\n');
    procesarComando(linea);
  }

  // 2) Cada cierto intervalo, leer sensores y enviar datos
  unsigned long ahora = millis();
  if (ahora - ultimoEnvio >= INTERVALO_ENVIO) {
    ultimoEnvio = ahora;

    // Leer sensores
    int lecturaZ1 = analogRead(PIN_SENSOR_Z1);
    int lecturaZ2 = analogRead(PIN_SENSOR_Z2);

    float humedadZ1 = calcularHumedad(lecturaZ1, Z1_VALOR_SECO, Z1_VALOR_MOJADO);
    float humedadZ2 = calcularHumedad(lecturaZ2, Z2_VALOR_SECO, Z2_VALOR_MOJADO);

    // Enviar en una sola línea
    Serial.print("DATA;");
    Serial.print("Z1_RAW=");
    Serial.print(lecturaZ1);
    Serial.print(";Z1_HUM=");
    Serial.print(humedadZ1, 2);
    Serial.print(";Z2_RAW=");
    Serial.print(lecturaZ2);
    Serial.print(";Z2_HUM=");
    Serial.println(humedadZ2, 2);
  }
}


