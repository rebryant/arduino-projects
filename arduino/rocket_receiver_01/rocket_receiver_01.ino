

// Code to run on Arduino serving as rocket ground station
// Repeatedly receives data from rocket computer and uploads via serial line to a connected processor
// Prefixes message with 8 characters including RSSI

// Print barebones (0) or general information?  
#define PRINT 0

// Offset for message 
#define OFFSET_MESSAGE 8

// Feather9x_RX
// -*- mode: C++ -*-
// Example sketch showing how to create a simple messaging client (receiver)
// with the RH_RF95 class. RH_RF95 class does not provide for addressing or
// reliability, so you should only use RH_RF95 if you do not need the higher
// level messaging abilities.
// It is designed to work with the other example Feather9x_TX

#include <SPI.h>
#include <RH_RF95.h>


// First 3 here are boards w/radio BUILT-IN. Boards using FeatherWing follow.
#if defined (__AVR_ATmega32U4__)  // Feather 32u4 w/Radio
  #define RFM95_CS    8
  #define RFM95_INT   7
  #define RFM95_RST   4

#elif defined(ADAFRUIT_FEATHER_M0) || defined(ADAFRUIT_FEATHER_M0_EXPRESS) || defined(ARDUINO_SAMD_FEATHER_M0)  // Feather M0 w/Radio
  #define RFM95_CS    8
  #define RFM95_INT   3
  #define RFM95_RST   4

#elif defined(ARDUINO_ADAFRUIT_FEATHER_RP2040_RFM)  // Feather RP2040 w/Radio
  #define RFM95_CS   16
  #define RFM95_INT  21
  #define RFM95_RST  17

#elif defined (__AVR_ATmega328P__)  // Feather 328P w/wing
  #define RFM95_CS    4  //
  #define RFM95_INT   3  //
  #define RFM95_RST   2  // "A"

#elif defined(ESP8266)  // ESP8266 feather w/wing
  #define RFM95_CS    2  // "E"
  #define RFM95_INT  15  // "B"
  #define RFM95_RST  16  // "D"

#elif defined(ARDUINO_ADAFRUIT_FEATHER_ESP32S2) || defined(ARDUINO_NRF52840_FEATHER) || defined(ARDUINO_NRF52840_FEATHER_SENSE)
  #define RFM95_CS   10  // "B"
  #define RFM95_INT   9  // "A"
  #define RFM95_RST  11  // "C"

#elif defined(ESP32)  // ESP32 feather w/wing
  #define RFM95_CS   33  // "B"
  #define RFM95_INT  27  // "A"
  #define RFM95_RST  13

#elif defined(ARDUINO_NRF52832_FEATHER)  // nRF52832 feather w/wing
  #define RFM95_CS   11  // "B"
  #define RFM95_INT  31  // "C"
  #define RFM95_RST   7  // "A"

#endif

/* Some other possible setups include:

// Feather 32u4:
#define RFM95_CS   8
#define RFM95_RST  4
#define RFM95_INT  7

// Feather M0:
#define RFM95_CS   8
#define RFM95_RST  4
#define RFM95_INT  3

// Arduino shield:
#define RFM95_CS  10
#define RFM95_RST  9
#define RFM95_INT  7

// Feather 32u4 w/wing:
#define RFM95_RST 11  // "A"
#define RFM95_CS  10  // "B"
#define RFM95_INT  2  // "SDA" (only SDA/SCL/RX/TX have IRQ!)

// Feather m0 w/wing:
#define RFM95_RST 11  // "A"
#define RFM95_CS  10  // "B"
#define RFM95_INT  6  // "D"
*/

// Change to 434.0 or other frequency, must match RX's freq!
#define RF95_FREQ 915.0

// Singleton instance of the radio driver
RH_RF95 rf95(RFM95_CS, RFM95_INT);

////////////////// Definitions for communicating with rocket flight computer



void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);

  Serial.begin(115200);
#if PRINT
  while (!Serial) delay(1);
  delay(100);
  Serial.println("Rocket ground station");
#endif

  // manual reset
  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  while (!rf95.init()) {
#if PRINT
    Serial.println("LoRa radio init failed");
    Serial.println("Uncomment '#define SERIAL_DEBUG' in RH_RF95.cpp for detailed debug info");
#endif
    while (1);
  }
#if PRINT
  Serial.println("LoRa radio init OK!");
#endif

  // Defaults after init are 434.0MHz, modulation GFSK_Rb250Fd250, +13dbM
  if (!rf95.setFrequency(RF95_FREQ)) {
  #if PRINT
    Serial.println("setFrequency failed");
  #endif
    while (1);
  }
#if PRINT
  Serial.print("Set Freq to: "); Serial.println(RF95_FREQ);
#endif

  // Defaults after init are 434.0MHz, 13dBm, Bw = 125 kHz, Cr = 4/5, Sf = 128chips/symbol, CRC on

  // The default transmitter power is 13dBm, using PA_BOOST.
  // If you are using RFM95/96/97/98 modules which uses the PA_BOOST transmitter pin, then
  // you can set transmitter powers from 5 to 23 dBm:
  rf95.setTxPower(23, false);
}


void loop() {
  static unsigned last_receive_count = 0;
  static unsigned receive_count = 0;
  static bool led_high = true;
  if (receive_count - last_receive_count >= 5) {
     digitalWrite(LED_BUILTIN, led_high ? HIGH : LOW);
     led_high = !led_high;
     last_receive_count = receive_count;
  }
  if (rf95.available()) {
    // Should be a message for us now
    uint8_t buf[OFFSET_MESSAGE+RH_RF95_MAX_MESSAGE_LEN+1];
    memset(buf, 0, sizeof(buf));
    uint8_t *rbuf = buf+OFFSET_MESSAGE;
    uint8_t rlen = RH_RF95_MAX_MESSAGE_LEN;
    if (rf95.recv(rbuf, &rlen)) {
      receive_count++;
      itoa(rf95.lastRssi(), (char *) buf, DEC);
      for (int i = 0; i < OFFSET_MESSAGE; i++)
        if (buf[i] == 0)
          buf[i] = ' ';
#if PRINT
      Serial.print("Message: ");
      Serial.print((char *) buf);
      Serial.print("  RSSI: ");
      Serial.println(rf95.lastRssi(), DEC);
#else
      Serial.println((char *) buf);
#endif
    } else {
      delay(100);
#if PRINT
      Serial.println("Receive failed");
#endif
    }
  } else
    delay(100);
}
