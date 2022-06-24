/*

  Arduino Nicla Sense ME WEB Bluetooth® Low Energy Sense dashboard demo


  Hardware required: https://store.arduino.cc/nicla-sense-me

  1) Upload this sketch to the Arduino Nano BLE sense board

  2) Open the following web page in the Chrome browser:
  https://arduino.github.io/ArduinoAI/NiclaSenseME-dashboard/

  3) Click on the green button in the web page to connect the browser to the board over Bluetooth® Low Energy


  Web dashboard by D. Pajak

  Device sketch based on example by Sandeep Mistry and Massimo Banzi
  Sketch and web dashboard copy-fixed to be used with the Nicla Sense ME by Pablo Marquínez

  */

  #include "Nicla_System.h"
  #include "Arduino_BHY2.h"
  #include <ArduinoBLE.h>

  #define BLE_SENSE_UUID(val) ("19b10000" val "-537e-4f6c-d104768a1214")

  const int VERSION = 0x00000001;

  BLEService service(BLE_SENSE_UUID("0000"));

  BLEUnsignedIntCharacteristic versionCharacteristic(BLE_SENSE_UUID("1001"), BLERead);
  BLECharacteristic accelerometerCharacteristic(BLE_SENSE_UUID("5001"), BLERead | BLENotify, 3 * sizeof(float));  // Array of 3x 2 Bytes, XY
  BLECharacteristic LinearAccelerationCharacteristic(BLE_SENSE_UUID("6001"), BLERead | BLENotify, 3 * sizeof(float));  // Array of 3x 2 Bytes, XY
  BLECharacteristic orientationCharacteristic(BLE_SENSE_UUID("9001"), BLERead | BLENotify, 3 * sizeof(int32_t));    // Array of 3x 4 Bytes, XYZ 
  BLECharacteristic quaternionCharacteristic(BLE_SENSE_UUID("7001"), BLERead | BLENotify, 4 * sizeof(float));     // Array of 4x 2 Bytes, XYZW
  BLECharacteristic rgbLedCharacteristic(BLE_SENSE_UUID("8001"), BLERead | BLEWrite, 3 * sizeof(byte)); // Array of 3 bytes, RGB

  // String to calculate the local and device name
  String name;

  SensorOrientation orientation(SENSOR_ID_ORI); 
  SensorQuaternion quaternion(SENSOR_ID_RV);
  SensorXYZ accelerometer(SENSOR_ID_ACC);
  SensorXYZ linearAcceleration(SENSOR_ID_LACC);


  void setup(){
    Serial.begin(115200);

    Serial.println("Start");

    nicla::begin();
    nicla::leds.begin();
    nicla::leds.setColor(green);

    //Sensors initialization
    BHY2.begin();
    orientation.begin();
    accelerometer.begin();
    quaternion.begin();
    linearAcceleration.begin();
    if (!BLE.begin()){
      Serial.println("Failed to initialized Bluetooth® Low Energy!");

      while (1)
        ;
    }

    String address = BLE.address();

    Serial.print("address = ");
    Serial.println(address);

    address.toUpperCase();

    name = "BLESense-";
    name += address[address.length() - 5];
    name += address[address.length() - 4];
    name += address[address.length() - 2];
    name += address[address.length() - 1];

    Serial.print("name = ");
    Serial.println(name);

    BLE.setLocalName(name.c_str());
    BLE.setDeviceName(name.c_str());
    BLE.setAdvertisedService(service);

    // Add all the previously defined Characteristics

    service.addCharacteristic(versionCharacteristic);
    
    service.addCharacteristic(orientationCharacteristic);
    service.addCharacteristic(accelerometerCharacteristic);
    service.addCharacteristic(quaternionCharacteristic);
    service.addCharacteristic(rgbLedCharacteristic);
    service.addCharacteristic(LinearAccelerationCharacteristic);
    //service.addCharacteristic(orientationCharacteristic);


    

    // Disconnect event handler
    BLE.setEventHandler(BLEDisconnected, blePeripheralDisconnectHandler);
    
    // Sensors event handlers

    rgbLedCharacteristic.setEventHandler(BLEWritten, onRgbLedCharacteristicWrite);

    versionCharacteristic.setValue(VERSION);

    BLE.addService(service);
    BLE.advertise();
  }

  void loop(){
    while (BLE.connected()){
      BHY2.update();

     if (orientationCharacteristic.subscribed()){
        float x, y, z;

        x = orientation.pitch();
        y = orientation.roll();
        z = orientation.heading();

        int16_t oriValues[3] = {x, y, z};

        orientationCharacteristic.writeValue(oriValues, sizeof(oriValues));
      }
      if (accelerometerCharacteristic.subscribed()){
        float x, y, z;
        x = accelerometer.x();
        y = accelerometer.y();
        z = accelerometer.z();

        float accelerometerValues[] = {x, y, z};
        accelerometerCharacteristic.writeValue(accelerometerValues, sizeof(accelerometerValues));
      }
      if (LinearAccelerationCharacteristic.subscribed()){
        float x, y, z;
        x = linearAcceleration.x();
        y = linearAcceleration.y();
        z = linearAcceleration.z();

        float accelerometerValues[] = {x, y, z};
        LinearAccelerationCharacteristic.writeValue(accelerometerValues, sizeof(accelerometerValues));
      }
      if(quaternionCharacteristic.subscribed()){
        float x, y, z, w;
        x = quaternion.x();
        y = quaternion.y();
        z = quaternion.z();
        w = quaternion.w();

        float quaternionValues[] = {x,y,z,w};
        quaternionCharacteristic.writeValue(quaternionValues, sizeof(quaternionValues));
      }

    }
  }

  void blePeripheralDisconnectHandler(BLEDevice central){
    nicla::leds.setColor(red);
  }

 

  void onRgbLedCharacteristicWrite(BLEDevice central, BLECharacteristic characteristic){
    byte r = rgbLedCharacteristic[0];
    byte g = rgbLedCharacteristic[1];
    byte b = rgbLedCharacteristic[2];

    nicla::leds.setColor(r, g, b);
  }
