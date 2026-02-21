
void setup() {

  //Setting that I write to pin 13
  pinMode(13, OUTPUT);
}

// The loop function runs over and over again forever
void loop() {

  digitalWrite(12, HIGH);   // Turn the LED on (HIGH is the voltage level)
  delay(1000);                      // Wait for a second (1000 milliseconds)
  
  digitalWrite(12, LOW);    // Turn the LED off by making the voltage LOW
  delay(1000);                       // Wait for a second
}