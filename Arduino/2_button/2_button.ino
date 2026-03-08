
int led_Pin = 12;
int button_pin = 2;

void setup() {

  //Setting that I write to pin 13
  pinMode(led_Pin, OUTPUT);
  pinMode(2, INPUT);
}

// The loop function runs over and over again forever
void loop() {
  if (digitalRead(button_pin) == HIGH) {
    digitalWrite(led_Pin, HIGH);
  } else {
    digitalWrite(led_Pin, LOW);
  }

}