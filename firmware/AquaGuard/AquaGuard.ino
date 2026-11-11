
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ==================================================
// AQUAGUARD - SMART WATER TANK MONITORING SYSTEM
// Board: Arduino Uno R3
// ==================================================


// ==================================================
// 1. OLED CONFIGURATION
// ==================================================

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_ADDRESS 0x3C

Adafruit_SSD1306 display(
  SCREEN_WIDTH,
  SCREEN_HEIGHT,
  &Wire,
  OLED_RESET
);

bool oledReady = false;


// ==================================================
// 2. DS18B20 TEMPERATURE SENSOR
// ==================================================

#define TEMP_PIN 2

OneWire oneWire(TEMP_PIN);
DallasTemperature tempSensor(&oneWire);


// ==================================================
// 3. HC-SR04 ULTRASONIC SENSOR
// ==================================================

#define TRIG_PIN 9
#define ECHO_PIN 10


// ==================================================
// 4. WATER LEVEL SENSOR
// ==================================================

#define WATER_PIN A0

const int WATER_THRESHOLD = 300;


// ==================================================
// 5. BUZZER CONFIGURATION
// ==================================================

#define BUZZER_PIN 7

// Previously tested successfully with this module
const bool BUZZER_ACTIVE_LOW = true;

// Buzzer activates when distance is 15 cm or less
const float ALARM_DISTANCE_CM = 15.0;


// ==================================================
// 6. READ ULTRASONIC DISTANCE
// ==================================================

float readDistance() {

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(
    ECHO_PIN,
    HIGH,
    30000UL
  );

  if (duration == 0) {
    return -1.0;
  }

  float distance =
    (duration * 0.0343) / 2.0;

  return distance;
}


// ==================================================
// 7. BUZZER CONTROL
// ==================================================

void setBuzzer(bool alarmActive) {

  if (BUZZER_ACTIVE_LOW) {

    digitalWrite(
      BUZZER_PIN,
      alarmActive ? LOW : HIGH
    );

  } else {

    digitalWrite(
      BUZZER_PIN,
      alarmActive ? HIGH : LOW
    );
  }
}


// ==================================================
// 8. PROFESSIONAL OLED DISPLAY
// ==================================================

void updateDisplay(
  float temperature,
  bool temperatureValid,
  float distance,
  int waterValue,
  bool waterDetected
) {

  if (!oledReady) {
    return;
  }

  bool buzzerOn =
    (distance >= 0 &&
     distance <= ALARM_DISTANCE_CM);

  display.clearDisplay();

  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);


  // ----------------------------------------------
  // HEADER
  // ----------------------------------------------

  display.setCursor(0, 0);
  display.print("AQUAGUARD");

  display.setCursor(96, 0);

  if (temperatureValid && distance >= 0) {
    display.print("OK");
  } else {
    display.print("CHECK");
  }

  display.drawFastHLine(
    0, 10, 128,
    SSD1306_WHITE
  );


  // ----------------------------------------------
  // TEMPERATURE CARD
  // ----------------------------------------------

  display.drawRoundRect(
    0, 13, 76, 35, 4,
    SSD1306_WHITE
  );

  display.setTextSize(1);
  display.setCursor(5, 17);
  display.print("TEMP");

  if (temperatureValid) {

    display.setCursor(5, 28);

    if (temperature < -9.9 || temperature >= 100.0) {
      display.setTextSize(1);
    } else {
      display.setTextSize(2);
    }

    display.print(temperature, 1);
    display.print("C");

  } else {

    display.setTextSize(1);
    display.setCursor(5, 30);
    display.print("ERROR");
  }


  // ----------------------------------------------
  // WATER STATUS CARD
  // ----------------------------------------------

  display.drawRoundRect(
    80, 13, 48, 35, 4,
    SSD1306_WHITE
  );

  display.setTextSize(1);
  display.setCursor(84, 17);
  display.print("WATER");

  display.setTextSize(2);
  display.setCursor(84, 28);

  if (waterDetected) {
    display.print("WET");
  } else {
    display.print("DRY");
  }


  // ----------------------------------------------
  // BOTTOM INFORMATION BAR
  // ----------------------------------------------

  display.drawFastHLine(
    0, 51, 128,
    SSD1306_WHITE
  );

  display.setTextSize(1);


  // Distance
  display.setCursor(0, 55);
  display.print("D:");

  if (distance >= 0) {

    display.print(distance, 1);
    display.print("cm");

  } else {

    display.print("--");
  }


  // Water sensor raw value
  display.setCursor(48, 55);
  display.print("S:");
  display.print(waterValue);


  // Buzzer status
  display.setCursor(91, 55);
  display.print("BZ:");
  display.print(buzzerOn ? "ON" : "OFF");


  // Refresh screen
  display.display();
}


// ==================================================
// 9. SETUP
// ==================================================

void setup() {

  Serial.begin(9600);


  // HC-SR04
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);


  // Buzzer
  pinMode(BUZZER_PIN, OUTPUT);
  setBuzzer(false);


  // DS18B20
  tempSensor.begin();
  tempSensor.setResolution(10);


  // OLED
  if (
    display.begin(
      SSD1306_SWITCHCAPVCC,
      OLED_ADDRESS
    )
  ) {

    oledReady = true;

    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);

    display.setCursor(15, 20);
    display.println("AQUAGUARD");

    display.setCursor(15, 35);
    display.println("SYSTEM STARTING");

    display.display();

  } else {

    Serial.println("ERROR: OLED NOT FOUND");
  }


  // Startup information
  Serial.println("========================");
  Serial.println("AQUAGUARD SYSTEM STARTED");
  Serial.println("========================");

  Serial.print("DS18B20 Sensors Found: ");
  Serial.println(tempSensor.getDeviceCount());

  Serial.println("Serial Baud Rate: 9600");

  delay(1500);
}


// ==================================================
// 10. MAIN LOOP
// ==================================================

void loop() {


  // ----------------------------------------------
  // READ TEMPERATURE
  // ----------------------------------------------

  tempSensor.requestTemperatures();

  float temperatureC =
    tempSensor.getTempCByIndex(0);

  bool temperatureValid =
    (temperatureC != DEVICE_DISCONNECTED_C);


  // ----------------------------------------------
  // READ ULTRASONIC DISTANCE
  // ----------------------------------------------

  float distance = readDistance();


  // ----------------------------------------------
  // READ WATER SENSOR
  // ----------------------------------------------

  int waterValue =
    analogRead(WATER_PIN);

  bool waterDetected =
    (waterValue >= WATER_THRESHOLD);


  // ----------------------------------------------
  // BUZZER CONTROL
  // ----------------------------------------------

  bool alarmActive = false;

  if (
    distance >= 0 &&
    distance <= ALARM_DISTANCE_CM
  ) {

    alarmActive = true;
  }

  setBuzzer(alarmActive);


  // ----------------------------------------------
  // UPDATE OLED
  // ----------------------------------------------

  updateDisplay(
    temperatureC,
    temperatureValid,
    distance,
    waterValue,
    waterDetected
  );


  // ----------------------------------------------
  // SERIAL OUTPUT FOR PYTHON DASHBOARD
  // ----------------------------------------------

  Serial.println("----------------------");


  // Temperature
  Serial.print("Temperature: ");

  if (temperatureValid) {

    Serial.print(temperatureC, 2);
    Serial.println(" Celsius");

  } else {

    Serial.println("ERROR - Sensor not detected");
  }


  // Distance
  Serial.print("Distance: ");

  if (distance >= 0) {

    Serial.print(distance, 2);
    Serial.println(" cm");

  } else {

    Serial.println("NO ECHO");
  }


  // Water sensor
  Serial.print("Water Sensor: ");
  Serial.print(waterValue);

  Serial.print(" | Status: ");

  Serial.println(
    waterDetected ? "WET" : "DRY"
  );


  // Buzzer
  Serial.print("Buzzer: ");

  Serial.println(
    alarmActive ? "ON" : "OFF"
  );


  Serial.println("----------------------");


  // Update interval
  delay(300);
}
