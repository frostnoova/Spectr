#include "CyberLib.h"
#define FASTADC 1
#ifndef cbi
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#endif
#ifndef sbi
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))
#endif

bool started = false;
byte buf[7];
unsigned long ttime = 0;
unsigned int adc = 0;
bool ch1 = LOW;

void setup() {
  DDRB = 0x00;
  D7_In;
  Serial.begin(500000);
#if FASTADC
  sbi(ADCSRA, ADPS2);
  sbi(ADCSRA, ADPS1);
  cbi(ADCSRA, ADPS0);
#endif

}

void loop() {

  if (Serial.available() > 0) {
    started = not started;
    char c = (char)Serial.read();
    if (c == 's') {
      while (c == 's') {
        ch1 = D7_Read;
        char c = (char)Serial.read();
        if (ch1 == HIGH) {
          started = true;
          Serial.println("started");
          break;
        }
        else if (c == 'e') {
          started = false;
          Serial.println("stopped");
          break;
        }
      }
    }
    else if (c == 'e') {
      started = false;
      Serial.println("stopped");
    }
  }
  if (started) {
    adc = analogRead(A3);
    ttime = micros();
    buf[0] = (PINB);
    buf[1] = (adc & 0xFF);
    buf[2] = (adc >> 8) & 0xFF;
    buf[3] = (ttime & 0x000000FF);
    buf[4] = (ttime & 0x0000FF00) >> 8;
    buf[5] = (ttime & 0x00FF0000) >> 16;
    buf[6] = (ttime & 0xFF000000) >> 24;
    Serial.write(buf, 7);
  }
}
