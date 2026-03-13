#include <Servo.h>

#define TRIG_PIN 6
#define ECHO_PIN 7

Servo gripper;
const int SERVO_PIN = 9;

// Servo angles (30-90 range)
const int OPEN_ANGLE  = 90;   // Fully open
const int CLOSE_ANGLE = 30;   // Fully closed
const int HALF_ANGLE  = 60;   // Half position
const int STEP_DELAY  = 15;

int currentAngle = OPEN_ANGLE;
bool servoAttached = false;
int lastReportedAngle = OPEN_ANGLE;  // Track last reported angle to reduce noise

// MODE CONTROL (ADDED)
bool manualMode = false;   // false = DIGITAL (UI control), true = MANUAL (sensor feedback)

// CALIBRATION VALUES - Update these after calibration!
// Distance in cm when gripper is at different angles
float DIST_AT_30 = 3.0;   // Distance at 30° (closed) - CALIBRATE THIS
float DIST_AT_90 = 12.0;  // Distance at 90° (open) - CALIBRATE THIS

unsigned long lastSensorRead = 0;
const int SENSOR_INTERVAL = 500; // Read sensor every 500ms (reduced from 200ms)

void setup() {
  Serial.begin(9600);
  delay(1000);
  
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  gripper.attach(SERVO_PIN);
  servoAttached = true;
  gripper.write(OPEN_ANGLE);  // Starts at 90° (open)
  currentAngle = OPEN_ANGLE;
  delay(500);
  
  gripper.detach();
  servoAttached = false;
  
  Serial.println("READY");
  Serial.println("Ultrasonic sensor enabled on D6/D7");
}

void loop() {
  // Continuously read sensor and send feedback (ONLY IN MANUAL MODE)
  if (millis() - lastSensorRead > SENSOR_INTERVAL) {

    if (manualMode) {   // <<< ADDED: sensor feedback only in MANUAL mode
      float distance = readDistanceCM();
      
      if (distance > 0) {
        // Convert distance to angle
        int detectedAngle = distanceToAngle(distance);
        
        // Only send if angle changed significantly (reduce noise and feedback loop)
        if (abs(detectedAngle - lastReportedAngle) > 3) {
          // Send sensor feedback
          Serial.print("SENSOR:");
          Serial.print(detectedAngle);
          Serial.print(",");
          Serial.println(distance);
          
          lastReportedAngle = detectedAngle;
        }
      }
    }
    
    lastSensorRead = millis();
  }
  
  // Handle commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    // MODE CONTROL COMMANDS (ADDED)
    if (command == "MODE:MANUAL") {
      manualMode = true;
      Serial.println("MODE:MANUAL");
    }
    else if (command == "MODE:DIGITAL") {
      manualMode = false;
      Serial.println("MODE:DIGITAL");
    }

    // MOVE SERVO ONLY IN DIGITAL MODE
    else if (command.startsWith("GRIP:") && !manualMode) {
      int targetAngle = command.substring(5).toInt();
      targetAngle = constrain(targetAngle, CLOSE_ANGLE, OPEN_ANGLE);
      moveToAngle(targetAngle);
    }

    else if (command == "STATUS") {
      Serial.print("POS:");
      Serial.println(currentAngle);
    }
    else if (command == "CALIBRATE") {
      calibrateSensor();
    }
  }
}

void moveToAngle(int targetAngle) {

  manualMode = false;   // <<< ADDED: force DIGITAL mode during motor movement

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
  lastReportedAngle = targetAngle;  // Update to prevent immediate sensor trigger
  delay(100);
  
  gripper.detach();
  servoAttached = false;
  
  // Send confirmation
  Serial.print("POS:");
  Serial.println(currentAngle);
}

float readDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return -1;

  return duration * 0.034 / 2;   // cm
}

int distanceToAngle(float distance) {
  // Constrain distance to valid range
  distance = constrain(distance, DIST_AT_30, DIST_AT_90);
  
  // Linear mapping: angle = map(distance, min_dist, max_dist, 30, 90)
  int angle = map(distance * 10, DIST_AT_30 * 10, DIST_AT_90 * 10, CLOSE_ANGLE, OPEN_ANGLE);
  
  // Constrain to valid angle range
  angle = constrain(angle, CLOSE_ANGLE, OPEN_ANGLE);
  
  return angle;
}

void calibrateSensor() {
  Serial.println("CALIBRATION_START");
  Serial.println("=== ULTRASONIC SENSOR CALIBRATION ===");
  
  // Move to closed position (30°)
  Serial.println("Moving to CLOSED (30°)...");
  gripper.attach(SERVO_PIN);
  gripper.write(CLOSE_ANGLE);
  delay(2000);
  
  // Read distance at 30°
  float dist30 = 0;
  for (int i = 0; i < 10; i++) {
    float d = readDistanceCM();
    if (d > 0) dist30 += d;
    delay(100);
  }
  dist30 = dist30 / 10;
  
  Serial.print("Distance at 30°: ");
  Serial.print(dist30);
  Serial.println(" cm");
  
  delay(1000);
  
  // Move to open position (90°)
  Serial.println("Moving to OPEN (90°)...");
  gripper.write(OPEN_ANGLE);
  delay(2000);
  
  // Read distance at 90°
  float dist90 = 0;
  for (int i = 0; i < 10; i++) {
    float d = readDistanceCM();
    if (d > 0) dist90 += d;
    delay(100);
  }
  dist90 = dist90 / 10;
  
  Serial.print("Distance at 90°: ");
  Serial.print(dist90);
  Serial.println(" cm");
  
  gripper.detach();
  
  Serial.println("\n=== CALIBRATION RESULTS ===");
  Serial.print("Update these values in code:\n");
  Serial.print("DIST_AT_30 = ");
  Serial.print(dist30, 1);
  Serial.println(";");
  Serial.print("DIST_AT_90 = ");
  Serial.print(dist90, 1);
  Serial.println(";");
  Serial.println("===========================");
  Serial.println("CALIBRATION_COMPLETE");
}
