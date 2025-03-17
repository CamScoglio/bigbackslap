#include <Stepper.h>

const int stepsPerRevolution = 200;
bool received = false;

Stepper myStepper(stepsPerRevolution, 9, 10, 11, 12);

void setup() {
  Serial.begin(9600);
  Serial.println("Arduino ready");
  myStepper.setSpeed(120); // MAX for default arduino motor
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    received = true;
  }

  if (received) {
    myStepper.step(stepsPerRevolution);
  }
}