#include <BMP180.h>
#include <SPI.h>
#include <SD.h>

File temperatureFile;
File timeFile;

BMP180 bmp;
MetricSystem metric;

// MISO on 13, MOSI on 12

int mode;
const int chipSelect = 10;

float volt;

int baroPin = A4;
int clockPin = A5;
unsigned long time;

void setup() {
  // put your setup code here, to run once:
    Serial.begin(9600);
    pinMode(chipSelect, OUTPUT);

    if (bmp.begin()) {
        Serial.println("BMP180 initialized!");
    } else {
        Serial.println("Sensor not found!");
    }
    bmp.setMetricSystem(MetricSystem());

    if (!SD.begin(chipSelect)) {

      Serial.println("initialization failed. Things to check:");
      Serial.println("1. is a card inserted?");
      Serial.println("2. is your wiring correct?");
      Serial.println("3. did you change the chipSelect pin to match your shield or module?");
      Serial.println("Note: press reset or reopen this serial monitor after fixing your issue!");

       while (true);
    }    
    Serial.println("initialization done.");

    SD.remove("pressure.txt"); //Remove file before writing
    SD.remove("temperature.txt");
    SD.remove("altitude.txt");
    SD.remove("time.txt");
    //temperatureFile = SD.open("temperature.txt", FILE_WRITE);
    //altitudeFile = SD.open("altitude.txt", FILE_WRITE);

    mode = 1;
}

void loop() {
  // put your main code here, to run repeatedly:
        time = millis();
        File pressureFile = SD.open("pressure.txt", FILE_WRITE);
        if (pressureFile) {
          Serial.println("Pressure File Found");
          pressureFile.println(bmp.readPressure());
          pressureFile.close();
        } 
        else {
          Serial.println("Pressure File not Found");
        }  
        Serial.print("Temperature: ");
        Serial.println(bmp.readTemperature());
        Serial.print("Pressure: ");
        Serial.println(bmp.readPressure());
        Serial.print("Altitude: ");
        Serial.println(bmp.readAltitude());

        delay(200);
}
    
