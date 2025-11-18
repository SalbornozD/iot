#include <Servo.h>

// ============================
// 1) Configuración de pines
// ============================

// Sensor de humedad
const int PIN_SENSOR_Z1 = A0;

// Servo
const int PIN_SERVO_Z1 = 9;

// ============================
// 2) Calibración de humedad
// ============================
int Z1_VALOR_SECO   = 1023;
int Z1_VALOR_MOJADO = 1;

// Envío de datos cada X ms
const unsigned long INTERVALO_ENVIO = 2000;
unsigned long ultimoEnvio = 0;

// Estado de riego (según último comando recibido)
bool riegoZ1 = false;

// Objeto Servo
Servo servoZ1;

// ============================
// 3) Ángulos de servos (MG995)
// ============================
// AJUSTA ESTOS VALORES según tu montaje
const int ANGULO_CERRADO = 20;   // válvula cerrada
const int ANGULO_ABIERTO = 120;  // válvula abierta

// ============================
// 4) Funciones auxiliares
// ============================

float calcularHumedad(int lectura, int valorSeco, int valorMojado) {
  float humedad = map(lectura, valorMojado, valorSeco, 100, 0);
  if (humedad < 0)   humedad = 0;
  if (humedad > 100) humedad = 100;
  return humedad;
}

// Movimiento entre ángulos con barrido corto
void moverServoSuave(Servo &servo, int desde, int hasta) {
  if (desde == hasta) return;

  if (desde < hasta) {
    for (int pos = desde; pos <= hasta; pos++) {
      servo.write(pos);
      delay(10);
    }
  } else {
    for (int pos = desde; pos >= hasta; pos--) {
      servo.write(pos);
      delay(10);
    }
  }
}

void abrirAgua(Servo &servo) {
  Serial.println("DEBUG abrirAgua(): barrido CERRADO -> ABIERTO");
  moverServoSuave(servo, ANGULO_CERRADO, ANGULO_ABIERTO);
}

void cerrarAgua(Servo &servo) {
  Serial.println("DEBUG cerrarAgua(): barrido ABIERTO -> CERRADO");
  moverServoSuave(servo, ANGULO_ABIERTO, ANGULO_CERRADO);
}

// Procesa una línea de comando proveniente de Django
// Formato esperado: RIEGO;Z1=1
void procesarComando(String linea) {
  linea.trim();

  Serial.print("Comando recibido bruto: ");
  Serial.println(linea);

  if (!linea.startsWith("RIEGO;")) {
    Serial.println(">> No es comando RIEGO, se ignora.");
    return;
  }

  // --- Procesar Z1 (solo si aparece Z1=) ---
  int idxZ1 = linea.indexOf("Z1=");
  if (idxZ1 >= 0 && idxZ1 + 3 < (int)linea.length()) {
    char c = linea.charAt(idxZ1 + 3);
    if (c == '1' && !riegoZ1) {
      riegoZ1 = true;
      Serial.println(">> Z1: cambia a 1 -> abrirAgua()");
      abrirAgua(servoZ1);
    } else if (c == '0' && riegoZ1) {
      riegoZ1 = false;
      Serial.println(">> Z1: cambia a 0 -> cerrarAgua()");
      cerrarAgua(servoZ1);
    } else {
      Serial.print(">> Z1 sin cambio, valor: ");
      Serial.println(c);
    }
  }

  // ACK de confirmación (solo Z1)
  Serial.print("ACK;");
  Serial.print("Z1=");
  Serial.println(riegoZ1 ? 1 : 0);
}

// ============================
// 5) Setup y loop principal
// ============================

void setup() {
  Serial.begin(9600);
  Serial.println("Sistema de Riego Arduino iniciado (1 zona).");

  servoZ1.attach(PIN_SERVO_Z1);

  // Dejar cerrado al inicio
  servoZ1.write(ANGULO_CERRADO);
  delay(500);

  riegoZ1 = false;
}

void loop() {
  // 1) Leer comandos
  if (Serial.available() > 0) {
    String linea = Serial.readStringUntil('\n');
    procesarComando(linea);
  }

  // 2) Enviar datos de sensor periódicamente
  unsigned long ahora = millis();
  if (ahora - ultimoEnvio >= INTERVALO_ENVIO) {
    ultimoEnvio = ahora;

    int lecturaZ1 = analogRead(PIN_SENSOR_Z1);
    float humedadZ1 = calcularHumedad(lecturaZ1, Z1_VALOR_SECO, Z1_VALOR_MOJADO);

    Serial.print("DATA;");
    Serial.print("Z1_RAW=");
    Serial.print(lecturaZ1);
    Serial.print(";Z1_HUM=");
    Serial.println(humedadZ1, 2);
  }
}

