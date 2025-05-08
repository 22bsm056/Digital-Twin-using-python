/*
 * Servo Digital Twin - Arduino Code
 * 
 * This sketch allows an Arduino to communicate with the Python Digital Twin application.
 * It controls a physical servo motor and reports back the actual position.
 * 
 * Communication Protocol:
 * - Receive: "S:angle\n" - Set servo to the specified angle (0-180)
 * - Send: "A:angle\n" - Report the current servo angle
 * 
 * Circuit:
 * - Servo signal pin connected to Arduino pin 9
 * - Servo power connected to 5V and GND
 * 
 * Optional: Add a potentiometer to analog pin A0 to manually control the servo
 */

#include <Servo.h>

#define SERVO_PIN 9         // Pin for servo control
#define POT_PIN A0          // Optional: Analog pin for potentiometer

// Communication settings
#define BAUD_RATE 9600      // Must match the Python application
#define COMMAND_TIMEOUT 20  // Milliseconds to wait for complete command
#define STATUS_INTERVAL 500 // Milliseconds between status updates

// Buffer for receiving commands
#define BUFFER_SIZE 20
char buffer[BUFFER_SIZE];
int bufferIndex = 0;

// Servo variables
Servo myServo;
int currentAngle = 90;      // Current angle (0-180)
int targetAngle = 90;       // Target angle for smooth movement
bool servoAttached = false; // Track servo attachment state

// Timing variables
unsigned long lastMoveTime = 0;    // Last servo movement time
unsigned long lastReportTime = 0;  // Last status report time
unsigned long lastCommandTime = 0;  // For command timeout

// Optional: Potentiometer variables
bool usePotentiometer = false;  // Set to true to enable potentiometer control
int lastPotValue = -1;          // Last read potentiometer value

void setup() {
  // Initialize serial communication
  Serial.begin(BAUD_RATE);
  while (!Serial && millis() < 3000) {
    // Wait for serial port to connect (max 3 seconds)
  }
  
  // Initialize the servo
  attachServo();
  
  // Move to initial position
  myServo.write(currentAngle);
  delay(500); // Give time for servo to reach position
  
  // Send initial status
  reportStatus();
  
  // Announce ready
  Serial.println("Ready");
}

void loop() {
  unsigned long currentTime = millis();
  
  // Read incoming serial data
  readSerialCommands();
  
  // Optional: Read potentiometer if enabled
  if (usePotentiometer) {
    readPotentiometer();
  }
  
  // Move servo toward target angle (smooth motion)
  updateServoPosition(currentTime);
  
  // Periodically report servo status
  if (currentTime - lastReportTime >= STATUS_INTERVAL) {
    reportStatus();
    lastReportTime = currentTime;
  }
}

// Process incoming serial data
void readSerialCommands() {
  while (Serial.available() > 0) {
    char inChar = (char)Serial.read();
    
    // Reset buffer on timeout
    unsigned long currentTime = millis();
    if (bufferIndex > 0 && currentTime - lastCommandTime > COMMAND_TIMEOUT) {
      bufferIndex = 0;
    }
    lastCommandTime = currentTime;
    
    // Process character
    if (inChar == '\n') {
      // Complete command received, process it
      buffer[bufferIndex] = '\0'; // Null-terminate
      processCommand(buffer);
      bufferIndex = 0; // Reset buffer
    } else if (bufferIndex < BUFFER_SIZE - 1) {
      // Add character to buffer
      buffer[bufferIndex++] = inChar;
    }
  }
}

// Process complete command
void processCommand(char* cmd) {
  // Check if command is to set servo angle (format: "S:angle")
  if (cmd[0] == 'S' && cmd[1] == ':') {
    int angle = atoi(&cmd[2]);
    
    // Validate angle
    if (angle >= 0 && angle <= 180) {
      // Set target angle
      targetAngle = angle;
      
      // Make sure servo is attached
      if (!servoAttached) {
        attachServo();
      }
      
      // Acknowledge command
      Serial.print("ACK:");
      Serial.println(angle);
    }
  }
}

// Update servo position (smooth movement)
void updateServoPosition(unsigned long currentTime) {
  // Move servo if target angle differs from current angle
  if (currentAngle != targetAngle && currentTime - lastMoveTime >= 15) {
    // Determine direction and step
    if (currentAngle < targetAngle) {
      currentAngle = min(currentAngle + 1, targetAngle);
    } else if (currentAngle > targetAngle) {
      currentAngle = max(currentAngle - 1, targetAngle);
    }
    
    // Update servo position
    if (servoAttached) {
      myServo.write(currentAngle);
    }
    
    lastMoveTime = currentTime;
  }
}

// Report current status to serial
void reportStatus() {
  Serial.print("A:");
  Serial.println(currentAngle);
}

// Optional: Read potentiometer value to control servo
void readPotentiometer() {
  if (!usePotentiometer) return;
  
  // Read analog value (0-1023) and map to servo range (0-180)
  int potValue = analogRead(POT_PIN);
  int mappedValue = map(potValue, 0, 1023, 0, 180);
  
  // Apply some debouncing to avoid jitter
  if (abs(mappedValue - lastPotValue) > 2) {
    targetAngle = mappedValue;
    lastPotValue = mappedValue;
  }
}

// Attach servo and handle potential failures
void attachServo() {
  // Try to attach the servo
  myServo.attach(SERVO_PIN);
  servoAttached = true;
  
  // Test if servo responds
  myServo.write(currentAngle);
}

// Detach servo to prevent jitter when idle (optional function)
void detachServo() {
  if (servoAttached) {
    myServo.detach();
    servoAttached = false;
  }
}
