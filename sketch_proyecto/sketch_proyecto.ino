#include <Servo.h>

// ============================
// 1) Configuración de pines
// ============================

// Sensor de humedad
const int PIN_SENSOR = A0;

// Servo
const int PIN_SERVO = 9;

// ============================
// 2) Calibración de humedad
// ============================
// Estos valores se ajustan según tus pruebas reales:
// - VALOR_SECO   -> lectura con tierra completamente seca
// - VALOR_MOJADO -> lectura con tierra muy húmeda / agua
int VALOR_SECO   = 1023;
int VALOR_MOJADO = 1;

// Envío de datos cada X ms
const unsigned long INTERVALO_ENVIO = 2000; // 10 segundos
unsigned long ultimoEnvio = 0;

// Estado de riego (según último comando recibido)
bool riego = false;

// Objeto Servo
Servo servo;

// ============================
// 3) Ángulos de servo (MG995)
// ============================
// AJUSTA ESTOS VALORES según tu montaje físico
const int ANGULO_CERRADO = 0;    // posición de válvula cerrada
const int ANGULO_ABIERTO = 180;  // posición de válvula abierta

// ============================
// 4) Funciones auxiliares
// ============================

/**
 * Calcula el porcentaje de humedad a partir de una lectura analógica.
 *
 * @param lectura     Valor leído del sensor (por ejemplo, 0–1023).
 * @param valorSeco   Lectura que corresponde a 0% de humedad (tierra seca).
 * @param valorMojado Lectura que corresponde a 100% de humedad (tierra muy húmeda).
 *
 * @return Porcentaje de humedad entre 0 y 100.
 */
float calcularHumedad(int lectura, int valorSeco, int valorMojado) {
  // Convierte la lectura del sensor al rango 0–100% usando map():
  // - valorMojado se interpreta como 100% de humedad
  // - valorSeco se interpreta como 0% de humedad
  float humedad = map(lectura, valorMojado, valorSeco, 100, 0);

  // Evita valores fuera del rango: si es menor que 0, fija en 0%
  if (humedad < 0)   humedad = 0;

  // Si es mayor que 100, fija en 100%
  if (humedad > 100) humedad = 100;

  return humedad;
}

/**
 * Mueve un servo suavemente desde un ángulo inicial hasta un ángulo final.
 *
 * El movimiento se hace grado a grado con pequeños retardos para que
 * el giro se vea más fluido y no tan brusco.
 *
 * @param servo  Objeto Servo que se va a controlar.
 * @param desde  Ángulo inicial (en grados).
 * @param hasta  Ángulo final (en grados).
 */
void moverServoSuave(Servo &servo, int desde, int hasta) {
  // Si los ángulos son iguales, no hay nada que mover.
  if (desde == hasta) return;

  // Si el ángulo inicial es menor, avanzamos de 'desde' a 'hasta'.
  if (desde < hasta) {
    for (int pos = desde; pos <= hasta; pos++) {
      servo.write(pos); // Mueve el servo a la posición actual.
      delay(10);        // Pausa corta para suavizar el movimiento.
    }
  } else {
    // Si el ángulo inicial es mayor, retrocedemos de 'desde' a 'hasta'.
    for (int pos = desde; pos >= hasta; pos--) {
      servo.write(pos); // Mueve el servo a la posición actual.
      delay(10);        // Pausa corta para suavizar el movimiento.
    }
  }
}

/**
 * Abre el paso de agua realizando un movimiento suave del servo.
 *
 * Usa los ángulos predefinidos:
 * - ANGULO_CERRADO: posición de válvula cerrada
 * - ANGULO_ABIERTO: posición de válvula abierta
 *
 * @param servo Objeto Servo que controla la válvula.
 */
void abrirAgua(Servo &servo) {
  // Mensaje de depuración para el monitor serie.
  Serial.println("DEBUG abrirAgua(): barrido CERRADO -> ABIERTO");

  // Mueve el servo desde la posición de cerrado hasta la de abierto.
  moverServoSuave(servo, ANGULO_CERRADO, ANGULO_ABIERTO);
}

/**
 * Cierra el paso de agua realizando un movimiento suave del servo.
 *
 * Usa los ángulos predefinidos:
 * - ANGULO_ABIERTO: posición de válvula abierta
 * - ANGULO_CERRADO: posición de válvula cerrada
 *
 * @param servo Objeto Servo que controla la válvula.
 */
void cerrarAgua(Servo &servo) {
  // Mensaje de depuración para el monitor serie.
  Serial.println("DEBUG cerrarAgua(): barrido ABIERTO -> CERRADO");

  // Mueve el servo desde la posición de abierto hasta la de cerrado.
  moverServoSuave(servo, ANGULO_ABIERTO, ANGULO_CERRADO);
}

/**
 * Procesa un comando recibido por puerto serie para controlar el riego.
 *
 * Formato esperado:
 *   RIEGO;1  -> abrir llave
 *   RIEGO;0  -> cerrar llave
 *
 * Lógica:
 * - Ignora cualquier línea que no empiece con "RIEGO;".
 * - Lee el carácter inmediatamente después del ';' (0 o 1).
 * - Solo mueve el servo si el estado cambia (para evitar movimientos repetidos).
 * - Envía un ACK al final con el estado actual (por ahora usando la etiqueta "Z1=").
 */
void procesarComando(String linea) {
  // Elimina espacios en blanco y saltos de línea al inicio y al final.
  linea.trim();

  Serial.print("Comando recibido bruto: ");
  Serial.println(linea);

  // Verificar si el comando comienza con "RIEGO;"
  if (!linea.startsWith("RIEGO;")) {
    Serial.println(">> No es comando RIEGO, se ignora.");
    return;
  }

  // El formato esperado es "RIEGO;0" o "RIEGO;1".
  // "RIEGO;" tiene 6 caracteres, así que el valor está en el índice 6.
  if (linea.length() < 7) {
    Serial.println(">> Comando RIEGO inválido: falta valor 0/1.");
    return;
  }

  // Toma el carácter después de "RIEGO;"
  char c = linea.charAt(6);

  if (c == '1') {
    // Solo abrimos si antes estaba en falso (evitamos repetir movimientos)
    if (!riego) {
      riego = true;
      Serial.println(">> RIEGO=1: abrirAgua()");
      abrirAgua(servo);
    } else {
      Serial.println(">> RIEGO=1 recibido pero ya estaba ABIERTO, sin cambio.");
    }
  }
  else if (c == '0') {
    // Solo cerramos si antes estaba en verdadero.
    if (riego) {
      riego = false;
      Serial.println(">> RIEGO=0: cerrarAgua()");
      cerrarAgua(servo);
    } else {
      Serial.println(">> RIEGO=0 recibido pero ya estaba CERRADO, sin cambio.");
    }
  }
  else {
    // Cualquier cosa distinta de '0' o '1' se considera inválida.
    Serial.print(">> Valor de RIEGO inválido (esperaba 0 o 1), recibido: ");
    Serial.println(c);
  }

  // ACK de confirmación: informamos el estado actual del riego.
  // Aunque ahora solo hay una zona, mantenemos "Z1=" si tu backend lo espera así.
  Serial.print("ACK;");
  Serial.print("Z1=");
  Serial.println(riego ? 1 : 0);
}

// ============================
// 5) Setup y loop principal
// ============================

/**
 * Configuración inicial del sistema de riego.
 *
 * - Inicia la comunicación serie para mensajes de depuración.
 * - Ata el servo al pin definido en PIN_SERVO.
 * - Coloca la válvula en posición de cerrado al inicio.
 * - Inicializa la variable de estado 'riego' en false (apagado).
 */
void setup() {
  // Inicia el puerto serie a 9600 baudios para ver mensajes en el monitor serie.
  Serial.begin(9600);
  Serial.println("Sistema de Riego Arduino iniciado.");

  // Asocia el objeto 'servo' al pin físico donde está conectado.
  servo.attach(PIN_SERVO);

  // Aseguramos que la llave comience cerrada:
  // ANGULO_CERRADO debe corresponder a la posición de válvula cerrada.
  servo.write(ANGULO_CERRADO);
  delay(500);  // Pausa breve para que el servo llegue a la posición.

  // Estado lógico del riego: false = cerrado / apagado.
  riego = false;
}

/**
 * Bucle principal del sistema de riego.
 *
 * Tareas:
 * 1) Escuchar comandos por el puerto serie y procesarlos.
 * 2) Leer periódicamente el sensor de humedad y enviar los datos por serie.
 */
void loop() {
  // 1) Leer comandos desde el puerto serie
  if (Serial.available() > 0) {
    // Lee una línea completa hasta el salto de línea '\n'
    String linea = Serial.readStringUntil('\n');

    // Procesa el comando recibido (por ejemplo: "RIEGO;1" o "RIEGO;0")
    procesarComando(linea);
  }

  // 2) Enviar datos del sensor periódicamente
  unsigned long ahora = millis();  // Tiempo actual desde que se encendió el Arduino (ms)

  // Verifica si ya pasó el intervalo definido para el siguiente envío
  if (ahora - ultimoEnvio >= INTERVALO_ENVIO) {
    ultimoEnvio = ahora;  // Actualiza el timestamp del último envío

    // Leer el valor crudo del sensor de humedad
    int lectura = analogRead(PIN_SENSOR);

    // Convertir la lectura cruda a porcentaje de humedad usando la calibración
    float humedad = calcularHumedad(lectura, VALOR_SECO, VALOR_MOJADO);

    // Enviar los datos en un formato fácil de parsear desde el backend:
    // Ejemplo de salida: DATA;HUM=45.23;RAW=678
    Serial.print("DATA");
    Serial.print(";HUM=");
    Serial.print(humedad, 2);  // 2 decimales para la humedad
    Serial.print(";RAW=");
    Serial.println(lectura);   // Cierra la línea con un salto de línea
  }
}


