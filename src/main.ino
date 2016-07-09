#include <AsyncMqttClient.h>
#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>

#define RPIN 13
#define GPIN 12
#define BPIN 14
#define LED_PIN 2

#ifndef WIFI_SSID
#define WIFI_SSID "your ssid"
#endif

#ifndef WIFI_PASS
#define WIFI_PASS "your wifi password"
#endif

#ifndef OTA_PASS
#define OTA_PASS "an ota pass"
#endif

#ifndef INSTANCE_NAME
#define INSTANCE_NAME "instance"
#endif

#ifndef PROJECT_NAME
#define PROJECT_NAME "project"
#endif

#ifndef MQTT_SERVER
#define MQTT_SERVER "test.mosquitto.org"
#endif

#define MQTT_PORT 1883
#define UDP_PORT 19872

WiFiUDP Udp;
WiFiClient wclient;
char COMMAND_TOPIC[] = PROJECT_NAME "/" INSTANCE_NAME "/command";
char STATE_TOPIC[] = PROJECT_NAME "/" INSTANCE_NAME "/state";
char LOG_TOPIC[] = PROJECT_NAME "/" INSTANCE_NAME "/log";

AsyncMqttClient mqttClient;


void color(int r, int g, int b) {
    analogWrite(RPIN, constrain(r, 0, 1023));
    analogWrite(GPIN, constrain(g, 0, 1023));
    analogWrite(BPIN, constrain(b, 0, 1023));
}


void onMqttConnect() {
    Serial.println("Connected to MQTT.");
    mqttClient.subscribe(COMMAND_TOPIC, 2);
    mqttPublish(LOG_TOPIC, "Connected.");
}


void onMqttDisconnect(AsyncMqttClientDisconnectReason reason) {
    mqttClient.connect();
}


void onMqttMessage(char* topic, char* payload, uint8_t qos, size_t len, size_t index, size_t total) {
    payload[len] = '\0';
    parseCommand((char *)payload);
}


void mqttPublish(String topic, String payload) {
    char chPayload[500];
    char chTopic[100];

    if (!mqttClient.connected()) {
        return;
    }

    topic.toCharArray(chTopic, 100);
    ("(" + String(millis()) + " - " + WiFi.localIP().toString() + ") " + INSTANCE_NAME + ": " + payload).toCharArray(chPayload, 100);
    mqttClient.publish(chTopic, 0, false, chPayload, 0);
}


void connectMQTT() {
    Serial.println("Connecting to MQTT...");

    mqttClient.onConnect(onMqttConnect);
    mqttClient.onDisconnect(onMqttDisconnect);
    mqttClient.onMessage(onMqttMessage);

    mqttClient.setServer(MQTT_SERVER, MQTT_PORT);
    mqttClient.setClientId(PROJECT_NAME "/" INSTANCE_NAME);

    mqttClient.connect();
}


// Receive a message from MQTT and act on it.
void mqttCallback(char* chTopic, byte* chPayload, unsigned int length) {
    chPayload[length] = '\0';
    parseCommand((char *)chPayload);
}


void connectWifi() {
    if (WiFi.waitForConnectResult() == WL_CONNECTED) {
        return;
    }

    resetPins();
    WiFi.persistent(false);
    WiFi.mode(WIFI_STA);
    while (WiFi.waitForConnectResult() != WL_CONNECTED) {
        WiFi.begin(WIFI_SSID, WIFI_PASS);
        Serial.println("Connecting to wifi...");
    }

    Serial.print("Wifi connected, IP address: ");
    Serial.println(WiFi.localIP());
}


void parseCommand(char* command) {
    int r, g, b;
    int i = 0;
    char *saveptr;
    char* text = strtok_r(command, ", ", &saveptr);
    while (text != NULL) {
        switch (i) {
        case 0:
            r = atoi(text);
            break;
        case 1:
            g = atoi(text);
            break;
        case 2:
            b = atoi(text);
            break;
        default:
            return;
        }
        i++;
        text = strtok_r(NULL, ", ", &saveptr);
    }
    color(r, g, b);
}


void readUDP() {
    byte packetBuffer[512];
    int noBytes = Udp.parsePacket();

    if (noBytes <= 0) {
        return;
    }

    Udp.read(packetBuffer, noBytes);
    packetBuffer[noBytes] = '\0';

    parseCommand((char *)packetBuffer);
}


void resetPins() {
    pinMode(1, OUTPUT);
    analogWrite(1, 0);
    pinMode(2, OUTPUT);
    analogWrite(2, 0);
    pinMode(3, OUTPUT);
    analogWrite(3, 0);
    pinMode(4, OUTPUT);
    analogWrite(4, 0);
    pinMode(5, OUTPUT);
    analogWrite(5, 0);
    pinMode(12, OUTPUT);
    analogWrite(12, 0);
    pinMode(13, OUTPUT);
    analogWrite(13, 0);
    pinMode(14, OUTPUT);
    analogWrite(14, 0);
    pinMode(15, OUTPUT);
    analogWrite(15, 0);
}


void setupmDNS() {
    char hostString[16] = {0};

    sprintf(hostString, "gameleds_%06X", ESP.getChipId());

    if (!MDNS.begin(hostString)) {
        Serial.println("Error setting up MDNS responder!");
    }

    MDNS.addService("gameleds", "udp", UDP_PORT);
}

void setup() {
    resetPins();
    pinMode(LED_PIN, OUTPUT);
    pinMode(RPIN, OUTPUT);
    pinMode(GPIN, OUTPUT);
    pinMode(BPIN, OUTPUT);

    Serial.begin(115200);
    Serial.println("Booting");

    setupmDNS();

    connectWifi();
    connectMQTT();

    Udp.begin(UDP_PORT);

    // Hostname defaults to esp8266-[ChipID]
    ArduinoOTA.setHostname(PROJECT_NAME "-" INSTANCE_NAME);

    ArduinoOTA.onStart([]() {
        resetPins();
        Serial.println("Start");
    });
    ArduinoOTA.onEnd([]() {
        Serial.println("\nEnd");
    });
    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
    });
    ArduinoOTA.onError([](ota_error_t error) {
        Serial.printf("Error[%u]: ", error);
        if (error == OTA_AUTH_ERROR) {
            Serial.println("Auth Failed");
        } else if (error == OTA_BEGIN_ERROR) {
            Serial.println("Begin Failed");
        } else if (error == OTA_CONNECT_ERROR) {
            Serial.println("Connect Failed");
        } else if (error == OTA_RECEIVE_ERROR) {
            Serial.println("Receive Failed");
        } else if (error == OTA_END_ERROR) {
            Serial.println("End Failed");
        }
    });
    ArduinoOTA.begin();
}

void flashLED() {
    // Blink for the first minute, just as a health test.
    if (millis() % 1000 > 100 || millis() > 60 * 1000) {
        digitalWrite(LED_PIN, HIGH);
    } else {
        digitalWrite(LED_PIN, LOW);
    }
}

// the loop function runs over and over again forever
void loop() {
    connectWifi();
    readUDP();
    flashLED();
    ArduinoOTA.handle();
}
