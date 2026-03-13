#include <Servo.h>

Servo gripper;
const int SERVO_PIN = 9;

// Servo angles (receives values from 30-90 from Python)
const int OPEN_ANGLE  = 90;   // Fully open
const int CLOSE_ANGLE = 30;   // Fully closed
const int HALF_ANGLE  = 60;   // Half position
const int STEP_DELAY  = 15;

int currentAngle = OPEN_ANGLE;
bool servoAttached = false;

void setup() {
  Serial.begin(9600);
  delay(1000);
  
  gripper.attach(SERVO_PIN);
  servoAttached = true;
  gripper.write(OPEN_ANGLE);  // Starts at 90° (open)
  currentAngle = OPEN_ANGLE;
  delay(500);
  
  gripper.detach();
  servoAttached = false;
  
  Serial.println("READY");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.startsWith("GRIP:")) {
      int targetAngle = command.substring(5).toInt();
      targetAngle = constrain(targetAngle, CLOSE_ANGLE, OPEN_ANGLE);
      moveToAngle(targetAngle);
    }
    else if (command == "STATUS") {
      Serial.print("POS:");
      Serial.println(currentAngle);
    }
    else if (command == "DEMO") {
      runDemo();
    }
  }
}

void moveToAngle(int targetAngle) {
  if (!servoAttached) {
    gripper.attach(SERVO_PIN);
    servoAttached = true;
    delay(50);
  }
  
  if (targetAngle < currentAngle) {
    for (int angle = currentAngle; angle >= targetAngle; angle--) {
      gripper.write(angle);
      delay(STEP_DELAY);
    }
  } else {
    for (int angle = currentAngle; angle <= targetAngle; angle++) {
      gripper.write(angle);
      delay(STEP_DELAY);
    }
  }
  
  currentAngle = targetAngle;
  delay(100);
  
  gripper.detach();
  servoAttached = false;
  
  Serial.print("POS:");
  Serial.println(currentAngle);
}

void runDemo() {
  Serial.println("DEMO_START");
  
  // Run exactly 2 cycles: 30° → 60° → 90° → 60° → 30°
  for (int cycle = 1; cycle <= 2; cycle++) {
    // Check if new command received (to allow stopping demo)
    if (Serial.available() > 0) {
      Serial.println("DEMO_STOPPED");
      return;
    }
    
    Serial.print("CYCLE:");
    Serial.println(cycle);
    
    // 1. Fully Close (30°) - wait 2 seconds
    moveToAngle(CLOSE_ANGLE);
    delay(2000);
    
    // 2. Half (60°) - wait 2 seconds
    moveToAngle(HALF_ANGLE);
    delay(2000);
    
    // 3. Fully Open (90°) - wait 2 seconds
    moveToAngle(OPEN_ANGLE);
    delay(2000);
    
    // 4. Back to Half (60°) - wait 2 seconds
    moveToAngle(HALF_ANGLE);
    delay(2000);
    
    // 5. Back to Fully Close (30°) - wait 2 seconds
    moveToAngle(CLOSE_ANGLE);
    delay(2000);
  }
  
  Serial.println("DEMO_END");
}