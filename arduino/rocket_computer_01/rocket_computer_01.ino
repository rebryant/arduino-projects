// Rocket flight computer.  Measures acceleration & altitude (via barometric pressure).  Transmits results to receiver via RFM95 LoRa Radio
// Randal E. Bryant.  2024-01-31

// Enable/disable printing over serial port  
#define PRINT 0
// Test while connected to USB
#define TETHERED 1
// Maximum number of transmissions
// Set to 30 minutes, assuming 3 transmissions per second
// #define MAX_TRANSMISSIONS (30*60*3)
// Number of extra transmissions after hitting MAX
#define EXTRA_TRANSMISSIONS 10
// How many samples are included in each transmission
#define RPT 4
// How often should the message be sent
// Settting RPT = 4 and FREQ = 2 makes it so that each sample is included in 2 messages
#define FREQ 2

// Design notes
// Challenge is to maximize number of samples per second received by receiver
// Find that requiring acknowledgements slows things down
// Instead, send each sample multiple times
// Also pack multiple samples per message to reduce number of transmissions
// Format message as ASCII string of fixed width with space character as separator.
// LoRa message up to 255 bytes long with 4-byte header.  Max payload = 251 bytes
// In current formulation, each message has 6-character header + 46 samples/character.
// Send 4 samples per message = 190 bytes with send frequency of one message every 2 samples
// Creates 2x redundancy


////////////////// Includes for Radio
// Feather9x_TX
// -*- mode: C++ -*-
// Example sketch showing how to create a simple messaging client (transmitter)
// with the RH_RF95 class. RH_RF95 class does not provide for addressing or
// reliability, so you should only use RH_RF95 if you do not need the higher
// level messaging abilities.
// It is designed to work with the other example Feather9x_RX

#include <SPI.h>
#include <RH_RF95.h>

////////////////// Includes for Pressure sensor

/***************************************************************************
  This is a library for the BMP3XX temperature & pressure sensor

  Designed specifically to work with the Adafruit BMP388 Breakout
  ----> http://www.adafruit.com/products/3966

  These sensors use I2C or SPI to communicate, 2 or 4 pins are required
  to interface.

  Adafruit invests time and resources providing this open source code,
  please support Adafruit and open-source hardware by purchasing products
  from Adafruit!

  Written by Limor Fried & Kevin Townsend for Adafruit Industries.
  BSD license, all text above must be included in any redistribution
 ***************************************************************************/

#include <Wire.h>
//#include <SPI.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP3XX.h>

////////////////// Includes for Accelerometer

//#include <Wire.h>
// #include <Adafruit_Sensor.h>
#include <Adafruit_ADXL375.h>

////////////////// Definitions for Radio

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

////////////////// Definitions for Pressure Sensor

#define BMP_SCK 13
#define BMP_MISO 12
#define BMP_MOSI 11
#define BMP_CS 10

#define SEALEVELPRESSURE_HPA (1013.25)

Adafruit_BMP3XX bmp;

////////////////// Definitions for Accelerometer

#define ADXL375_SCK 13
#define ADXL375_MISO 12
#define ADXL375_MOSI 11
#define ADXL375_CS 10

/* Assign a unique ID to this sensor at the same time */
/* Uncomment following line for default Wire bus      */
Adafruit_ADXL375 accel = Adafruit_ADXL375(12345);

/* Uncomment for software SPI */
//Adafruit_ADXL375 accel = Adafruit_ADXL375(ADXL375_SCK, ADXL375_MISO, ADXL375_MOSI, ADXL375_CS, 12345);

/* Uncomment for hardware SPI */
//Adafruit_ADXL375 accel = Adafruit_ADXL375(ADXL375_CS, &SPI, 12345);


////////////////// Definitions for Integration

// Buffer stores Header + RPT copies of message
// 2 digit max
#define WIDTH_RPT 3
// ID: 2 digit sender code
#define WIDTH_SENDER 3

// Header
#define OFFSET_RPT    0
#define OFFSET_SENDER (OFFSET_RPT+WIDTH_RPT)
#define HEADER_LENGTH  (OFFSET_SENDER+WIDTH_SENDER)


// Format data in fixed width fields.  Each field includes room for trailing blank
// Sequence Number
#define WIDTH_SEQUENCE 6
// X, Y, Z accelerations -xxxx.yy
#define WIDTH_ACCELERATION 9
// Altitude -xxx.xx
#define WIDTH_ALTITUDE 8
// Checksum HHHH
#define WIDTH_CHECK 5

#define OFFSET_SEQUENCE 0
#define OFFSET_X        (OFFSET_SEQUENCE+WIDTH_SEQUENCE)
#define OFFSET_Y        (OFFSET_X+WIDTH_ACCELERATION)
#define OFFSET_Z        (OFFSET_Y+WIDTH_ACCELERATION)
#define OFFSET_ALTITUDE (OFFSET_Z+WIDTH_ACCELERATION)
#define OFFSET_CHECK    (OFFSET_ALTITUDE+WIDTH_ALTITUDE)
#define MESSAGE_LENGTH  (OFFSET_CHECK+WIDTH_CHECK)

#define BUFFER_LENGTH (HEADER_LENGTH + RPT*MESSAGE_LENGTH)


// Own identifier
char my_id[WIDTH_SENDER] = "R1";

// Time between samples
#if PRINT
#define SAMPLE_INTERVAL 500
#else
#define SAMPLE_INTERVAL 0
#endif

uint32_t packetnum = 0;  // packet counter, we increment per xmission
uint8_t buf[BUFFER_LENGTH+1];
bool led_high = false;

void setup_sampler(int rpt) {
  memset(buf, ' ', BUFFER_LENGTH);
  buf[BUFFER_LENGTH] = 0;
  // Write header
  itoa(rpt, (char *) (buf+OFFSET_RPT), DEC);
  // Write ID
  memcpy(buf+OFFSET_SENDER, my_id, WIDTH_SENDER);
  // Make sure no NULLs in header
  for (int i = 0; i < HEADER_LENGTH; i++)
    if (buf[i] == 0)
      buf[i] = ' ';
}

////////////////// Setup serial port

void setup_serial() {
#if PRINT
  Serial.begin(115200);
  while (!Serial) delay(1);
  delay(100);
  Serial.println("Serial port ready!");
#endif
}

////////////////// Setup radio

void setup_radio() {
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);

  // manual reset
  digitalWrite(RFM95_RST, LOW);
  delay(10);
  digitalWrite(RFM95_RST, HIGH);
  delay(10);

  while (!rf95.init()) {
#if PRINT
    Serial.println("LoRa radio init failed");
    Serial.println("Uncomment '#define SERIAL_DEBUG' in RH_RF95.cpp for detailed debug info");
    while (1);
#endif
    delay (10);
  }

  // Defaults after init are 434.0MHz, modulation GFSK_Rb250Fd250, +13dbM
  if (!rf95.setFrequency(RF95_FREQ)) {
#if PRINT
    Serial.println("setFrequency failed");
    while (1);
#endif
    delay(10);
  }
#if PRINT
  Serial.print("Set Freq to: "); Serial.println(RF95_FREQ);
#endif

  // Defaults after init are 434.0MHz, 13dBm, Bw = 125 kHz, Cr = 4/5, Sf = 128chips/symbol, CRC on

  // The default transmitter power is 13dBm, using PA_BOOST.
  // If you are using RFM95/96/97/98 modules which uses the PA_BOOST transmitter pin, then
  // you can set transmitter powers from 5 to 23 dBm:
  rf95.setTxPower(23, false);

#if PRINT
  Serial.println("LoRa radio ready");
#endif

}

////////////////// Setup pressure sensor

void setup_pressure() {


  if (!bmp.begin_I2C()) {   // hardware I2C mode, can pass in address & alt Wire
  //if (! bmp.begin_SPI(BMP_CS)) {  // hardware SPI mode  
  //if (! bmp.begin_SPI(BMP_CS, BMP_SCK, BMP_MISO, BMP_MOSI)) {  // software SPI mode
#if PRINT
    Serial.println("Could not find a valid BMP3 sensor, check wiring!");
    while (1);
#endif
  }

  // Set up oversampling and filter initialization
  bmp.setTemperatureOversampling(BMP3_OVERSAMPLING_8X);
  bmp.setPressureOversampling(BMP3_OVERSAMPLING_4X);
  bmp.setIIRFilterCoeff(BMP3_IIR_FILTER_COEFF_3);
  bmp.setOutputDataRate(BMP3_ODR_50_HZ);
#if PRINT
  Serial.println("BMP Pressure Sensor ready");
#endif
}

////////////////// Setup accelerometer

void setup_accelerometer(void)
{
  
  /* Initialise the sensor */
  if(!accel.begin())
  {
    /* There was a problem detecting the ADXL375 ... check your connections */
  #if PRINT
    Serial.println("Ooops, no ADXL375 detected ... Check your wiring!");
    while(1);
  #endif
    delay(10);
  }

  // Range is fixed at +-200g

  /* Display some basic information on this sensor */
#if PRINT
  accel.printSensorDetails();
  // displayDataRate();
  Serial.println("");
  Serial.println("ADXL375 Accelerometer ready");
#endif
}

// General Code

void setup() {
  setup_serial();
  setup_pressure(); 
  setup_accelerometer();
  setup_radio();
  setup_sampler(RPT);
  packetnum = 0;
}

uint32_t checksum(char *sbuf, int len) { 
  uint32_t sum = 0;
  for (int i = 0; i < len; i++) {
    if (sbuf[i] == ' ') 
      continue;
    uint32_t residue = ((sum >> 15) & 0x1) + ((sum << 1) & 0xFFFE);
    sum = residue ^ sbuf[i]; 
  }
  return sum;
 }


// Grab data for one sample
// Store in appropriate region of buffer
void sample() {
  // Offset into buffer for this sample
  char *obuf = (char *) (buf + HEADER_LENGTH + MESSAGE_LENGTH * (packetnum % RPT));
  sensors_event_t event;
  accel.getEvent(&event);
  float X = event.acceleration.x;
  float Y = event.acceleration.y;
  float Z = event.acceleration.z;

  // Get pressure
  float altitude = 0.0;
  if (bmp.performReading()) {
    altitude = bmp.readAltitude(SEALEVELPRESSURE_HPA);
  }
  // Format into buffer
  memset(obuf, ' ', MESSAGE_LENGTH);
  itoa(packetnum, obuf+OFFSET_SEQUENCE, DEC);
  snprintf(obuf+OFFSET_X, WIDTH_ACCELERATION, "%.2f", X);
  snprintf(obuf+OFFSET_Y, WIDTH_ACCELERATION, "%.2f", Y);
  snprintf(obuf+OFFSET_Z, WIDTH_ACCELERATION, "%.2f", Z);
  snprintf(obuf+OFFSET_ALTITUDE, WIDTH_ALTITUDE, "%.2f", altitude);
  // Turn null characters into blanks
  for (int i = 0; i < MESSAGE_LENGTH; i++)
    if (obuf[i] == 0)
      obuf[i] = ' ';
  // Create crude checksum;
  uint32_t sum = checksum(obuf, OFFSET_CHECK);
  utoa(sum, obuf+OFFSET_CHECK, HEX); // Turn null characters into blanks
  for (int i = 0; i < MESSAGE_LENGTH; i++)
    if (obuf[i] == 0)
      obuf[i] = ' ';
// Make sure complete message is zero-terminated
buf[BUFFER_LENGTH] = 0;
packetnum++;
if (packetnum > MAX_TRANSMISSIONS)
  setup_sampler(0);
}

void loop() {
  if (packetnum > MAX_TRANSMISSIONS+EXTRA_TRANSMISSIONS) {
#if PRINT
    Serial.println("Exceeded transmission limit");
#endif
    while (1) {
      digitalWrite(LED_BUILTIN, LOW);
      delay(1000);
    }
  }
  if (packetnum % 10 == 0) {
    led_high = !led_high;
    digitalWrite(LED_BUILTIN, led_high ? HIGH : LOW);
  }
  sample();
  if (packetnum % FREQ == 0) {
    rf95.send(buf, BUFFER_LENGTH);
    delay(SAMPLE_INTERVAL);
    rf95.waitPacketSent();
#if PRINT
    Serial.print("Message: ");
    Serial.println((char *) buf);
#endif
#if TETHERED
    Serial.println((char *) buf);
#endif
  }
}
