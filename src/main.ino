#include <Wire.h>
#include <Arduino_GFX_Library.h>
#include <QMI8658.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <WiFiUDP.h>
#include <PubSubClient.h>
#include <math.h>

// ===================== WiFi =====================
const char* WIFI_SSID = "YungHub";
const char* WIFI_PASS = "yungyung";

// ===================== MQTT Broker =====================
const char* MQTT_HOST        = "mqtt.yungcz.com";
const int   MQTT_PORT        = 8883;
const char* MQTT_USERNAME    = "cartly";
const char* MQTT_PASSWORD    = "cartly";

const char* MQTT_TOPIC_PUB   = "smarttrolley/trolley_01/telemetry";
const char* MQTT_TOPIC_SUB   = "smarttrolley/trolley_01/config";
const char* DEVICE_ID        = "trolley_01";

// ===================== MQTT TLS CA =====================
static const char MQTT_ROOT_CA[] PROGMEM = R"EOF(
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
)EOF";

WiFiClientSecure net;
PubSubClient mqttClient(net);

static const uint32_t CLOUD_UPLOAD_MS  = 250;
uint32_t lastCloudUploadMs = 0;

// ===================== Direct Streaming (UDP) =====================
char     directHost[64]        = "";    // set via MQTT config: {"directHost":"x.x.x.x"}
uint16_t directPort            = 4210;
bool     directEnabled         = false; // set via MQTT config: {"directEnabled":true}
WiFiUDP  directUdp;
static const uint32_t DIRECT_UPLOAD_MS = 50;
uint32_t lastDirectUploadMs    = 0;

// ===================== Anchor SSIDs =====================
const char* ANCHOR_A = "ANCHOR_A";
const char* ANCHOR_B = "ANCHOR_B";
const char* ANCHOR_C = "ANCHOR_C";

// ===================== Pins =====================
static const int PIN_LCD_BL   = 20;
static const int PIN_LCD_DC   = 38;
static const int PIN_LCD_CS   = 39;
static const int PIN_LCD_SCK  = 40;
static const int PIN_LCD_MOSI = 41;
static const int PIN_LCD_RST  = 42;

static const int PIN_IMU_SDA  = 47;
static const int PIN_IMU_SCL  = 48;

static const int PIN_ENC_A    = 1;
static const int PIN_ENC_B    = 2;

// 你可以改成你实际接的 actuator 引脚
static const int PIN_ACTUATOR = 21;

// ===================== Display Colors =====================
static const uint16_t C_BLACK  = 0x0000;
static const uint16_t C_WHITE  = 0xFFFF;
static const uint16_t C_RED    = 0xF800;
static const uint16_t C_GREEN  = 0x07E0;
static const uint16_t C_BLUE   = 0x001F;
static const uint16_t C_CYAN   = 0x07FF;
static const uint16_t C_YELLOW = 0xFFE0;
static const uint16_t C_ORANGE = 0xFD20;
static const uint16_t C_GREY   = 0x8410;

// ===================== Display =====================
Arduino_DataBus *bus =
  new Arduino_ESP32SPI(PIN_LCD_DC, PIN_LCD_CS, PIN_LCD_SCK, PIN_LCD_MOSI, -1);

Arduino_GFX *gfx =
  new Arduino_ST7789(bus, PIN_LCD_RST, 0, true, 240, 240, 0, 0, 0, 0);

// ===================== IMU =====================
QMI8658 imu;

// ===================== Encoder =====================
volatile long encoderCount = 0;
volatile uint8_t prevAB = 0;
volatile uint32_t encIsrHits = 0;
uint32_t encoderPollHits = 0;

void IRAM_ATTR encoderISR() {
  encIsrHits++;
}

void pollEncoderFast() {
  static int lastA = -1;
  static uint32_t lastEdgeUs = 0;

  int a = digitalRead(PIN_ENC_A);

  if (lastA < 0) {
    lastA = a;
    return;
  }

  if (a != lastA) {
    uint32_t nowUs = micros();
    if (a == HIGH && nowUs - lastEdgeUs >= 100) {
      encoderCount += 1;
      encoderPollHits++;
      lastEdgeUs = nowUs;
    }
    lastA = a;
  }
}

// ===================== Wheel / Encoder =====================
// MMME uses a 6-pole magnetic disc on the wheel shaft.
// Counting rising edges on channel A gives 3 counts per wheel revolution.
static const float MOTOR_ENCODER_CPR = 3.0f;
static const float GEAR_RATIO        = 1.0f;
static const float COUNTS_PER_REV    = MOTOR_ENCODER_CPR * GEAR_RATIO;

static const float WHEEL_DIAM_M      = 0.0452f;
static const float WHEEL_CIRC_M      = WHEEL_DIAM_M * 3.1415926f;

// ===================== Timing =====================
static const uint32_t LOOP_MS              = 50;
static const uint32_t DISPLAY_PERIOD_MS    = 200;
static const uint32_t SERIAL_PERIOD_MS     = 250;
static const uint32_t DEFAULT_RSSI_SCAN_MS = 15000;
static const uint32_t WIFI_RETRY_MS        = 10000;
static const uint32_t MQTT_RETRY_MS        = 5000;

// ===================== Thresholds (remote configurable) =====================
float pickupAccelThreshold   = 2.5f;
float dropImpactThreshold    = 4.0f;
uint32_t queueDwellThreshold = 3000;
uint32_t dwellAlertThreshold = 4000;
uint32_t rssiScanIntervalMs  = DEFAULT_RSSI_SCAN_MS;
bool actuatorEnabled         = true;

// ===================== Heatmap =====================
static const int MAP_W = 20;
static const int MAP_H = 20;
static const float CELL_M = 0.5f;

uint16_t occupancy[MAP_H][MAP_W];
uint16_t dwellMap[MAP_H][MAP_W];
float posX_m = 0.0f, posY_m = 0.0f;
float yaw_rad = 0.0f;

// ===================== Metrics =====================
struct Metrics {
  float ax, ay, az;
  float gx, gy, gz;
  float aMag;
  float aDyn;
  float pitchDeg, rollDeg;
  float speed_mps;
  float dist_m;
  float stepCadence_spm;

  bool pickup;
  bool dropdown;
  uint32_t dwell_ms;

  String carryStyle;
  String loadProxy;
  bool browsing;
  bool queueDetect;

  int32_t anchorA_rssi;
  int32_t anchorB_rssi;
  int32_t anchorC_rssi;
  String zone;
  uint8_t anchorsSeen;

  bool imuOk;
  bool awsOk;
  String systemState;

  String hotspot;
};

Metrics M = {};

// ===================== State =====================
float gravX = 0, gravY = 0, gravZ = 0;
float dynRms = 0;
float speedSignedSmooth = 0.0f;
float speedAbsSmooth = 0.0f;
float vibEMA = 0;
float jerkEMA = 0;
float lastSpeedMps = 0;
float turnRateEMA = 0;
float lastSpeedForVar = 0;
float speedVarEMA = 0;

uint32_t lastLoopMs = 0;
uint32_t lastDisplayMs = 0;
uint32_t lastSerialMs = 0;
uint32_t lastRssiScanMs = 0;
uint32_t lastWiFiAttemptMs = 0;
uint32_t lastMQTTAttemptMs = 0;

uint32_t lastStepPeakMs = 0;
float cadenceEMA_spm = 0;
float adynFilt_dbg = 0.0f;  // exposed for display tuning

bool isLifted = false;
uint32_t lastPickupMs = 0;
uint32_t dwellStartMs = 0;
bool inDwell = false;

static const int STOPGO_BUF = 20;
uint8_t stopGoHistory[STOPGO_BUF];
int stopGoIdx = 0;
uint32_t lastStopGoMarkMs = 0;

// actuator pulse
bool actuatorActive = false;
uint32_t actuatorOffAt = 0;
bool anchorScanInProgress = false;
bool displayFlashActive = false;
uint32_t displayFlashOffAt = 0;
bool displayNeedsFullRedraw = false;

// ===================== Helpers =====================
float ema(float prev, float x, float alpha) {
  return alpha * x + (1.0f - alpha) * prev;
}

float absf(float x) {
  return x < 0 ? -x : x;
}

float clampf(float x, float lo, float hi) {
  if (x < lo) return lo;
  if (x > hi) return hi;
  return x;
}

float countsToMeters(long counts) {
  return ((float)counts / COUNTS_PER_REV) * WHEEL_CIRC_M;
}

void fatal(const char *msg) {
  Serial.println(msg);
  gfx->fillScreen(C_BLACK);
  gfx->setCursor(10, 10);
  gfx->setTextColor(C_RED);
  gfx->setTextSize(2);
  gfx->println("ERROR");
  gfx->setTextColor(C_WHITE);
  gfx->setTextSize(1);
  gfx->println(msg);
  while (1) delay(100);
}

void initMetrics() {
  M.ax = 0; M.ay = 0; M.az = 0;
  M.gx = 0; M.gy = 0; M.gz = 0;
  M.aMag = 0;
  M.aDyn = 0;
  M.pitchDeg = 0;
  M.rollDeg = 0;
  M.speed_mps = 0;
  M.dist_m = 0;
  M.stepCadence_spm = 0;

  M.pickup = false;
  M.dropdown = false;
  M.dwell_ms = 0;

  M.carryStyle = "ROLLING";
  M.loadProxy = "UNKNOWN";
  M.browsing = false;
  M.queueDetect = false;

  M.anchorA_rssi = -127;
  M.anchorB_rssi = -127;
  M.anchorC_rssi = -127;
  M.zone = "UNKNOWN";
  M.anchorsSeen = 0;

  M.imuOk = false;
  M.awsOk = false;
  M.systemState = "INIT";

  M.hotspot = "N/A";
}

void updateSystemState() {
  M.awsOk = mqttClient.connected();

  if (!M.imuOk) {
    M.systemState = "IMU_FAIL";
  } else if (M.anchorsSeen == 0) {
    M.systemState = "NO_ANCHOR";
  } else if (!M.awsOk) {
    M.systemState = "CLOUD_OFFLINE";
  } else if (M.anchorsSeen < 3) {
    M.systemState = "DEGRADED";
  } else {
    M.systemState = "NORMAL";
  }
}

// ===================== Actuator =====================
void actuatorOnFor(uint32_t ms) {
  if (!actuatorEnabled) return;
  digitalWrite(PIN_ACTUATOR, HIGH);
  actuatorActive = true;
  actuatorOffAt = millis() + ms;
}

void serviceActuator() {
  if (actuatorActive && (!actuatorEnabled || millis() >= actuatorOffAt)) {
    digitalWrite(PIN_ACTUATOR, LOW);
    actuatorActive = false;
  }
}

void flashDisplayFor(uint32_t ms) {
  if (ms == 0) return;
  displayFlashActive = true;
  displayFlashOffAt = millis() + ms;
}

void serviceDisplayFlash() {
  if (displayFlashActive && millis() >= displayFlashOffAt) {
    displayFlashActive = false;
    displayNeedsFullRedraw = true;
  }
}

// ===================== MQTT Config Callback =====================
String extractJsonValue(const String& payload, const String& key) {
  String pattern = "\"" + key + "\"";
  int keyPos = payload.indexOf(pattern);
  if (keyPos < 0) return "";

  int colon = payload.indexOf(':', keyPos);
  if (colon < 0) return "";

  int start = colon + 1;
  while (start < (int)payload.length() && (payload[start] == ' ' || payload[start] == '\"')) start++;

  int end = start;
  bool quoted = payload[colon + 1] == '\"' || (start > colon + 1 && payload[start - 1] == '\"');

  if (quoted) {
    end = payload.indexOf('\"', start);
    if (end < 0) return "";
  } else {
    while (end < (int)payload.length() &&
           payload[end] != ',' &&
           payload[end] != '}' &&
           payload[end] != '\n' &&
           payload[end] != '\r') {
      end++;
    }
  }

  return payload.substring(start, end);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }

  Serial.print("MQTT RX [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(msg);

  String v;

  v = extractJsonValue(msg, "pickupAccelThreshold");
  if (v.length()) pickupAccelThreshold = v.toFloat();

  v = extractJsonValue(msg, "dropImpactThreshold");
  if (v.length()) dropImpactThreshold = v.toFloat();

  v = extractJsonValue(msg, "queueDwellThreshold");
  if (v.length()) queueDwellThreshold = (uint32_t)v.toInt();

  v = extractJsonValue(msg, "dwellAlertThreshold");
  if (v.length()) dwellAlertThreshold = (uint32_t)v.toInt();

  v = extractJsonValue(msg, "rssiScanIntervalMs");
  if (v.length()) rssiScanIntervalMs = (uint32_t)v.toInt();

  v = extractJsonValue(msg, "actuatorEnabled");
  if (v == "true" || v == "1") actuatorEnabled = true;
  if (v == "false" || v == "0") actuatorEnabled = false;

  v = extractJsonValue(msg, "actuatorPulseMs");
  if (v.length()) actuatorOnFor((uint32_t)v.toInt());

  v = extractJsonValue(msg, "displayFlashMs");
  if (v.length()) flashDisplayFor((uint32_t)v.toInt());

  v = extractJsonValue(msg, "directHost");
  if (v.length()) v.toCharArray(directHost, sizeof(directHost));

  v = extractJsonValue(msg, "directPort");
  if (v.length()) directPort = (uint16_t)v.toInt();

  v = extractJsonValue(msg, "directEnabled");
  if (v == "true"  || v == "1") directEnabled = true;
  if (v == "false" || v == "0") directEnabled = false;
}

// ===================== Connectivity =====================
void connectWiFi(uint32_t nowMs) {
  if (WiFi.status() == WL_CONNECTED) return;
  if (nowMs - lastWiFiAttemptMs < WIFI_RETRY_MS) return;

  lastWiFiAttemptMs = nowMs;
  Serial.print("Connecting WiFi to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void connectMQTT(uint32_t nowMs) {
  if (mqttClient.connected()) return;
  if (WiFi.status() != WL_CONNECTED) return;
  if (nowMs - lastMQTTAttemptMs < MQTT_RETRY_MS) return;

  lastMQTTAttemptMs = nowMs;

  net.setCACert(MQTT_ROOT_CA);

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setKeepAlive(15);
  mqttClient.setSocketTimeout(2);

  Serial.print("Connecting to MQTT broker... ");
  if (mqttClient.connect(DEVICE_ID, MQTT_USERNAME, MQTT_PASSWORD)) {
    Serial.println("connected");
    mqttClient.subscribe(MQTT_TOPIC_SUB);
  } else {
    Serial.print("failed, rc=");
    Serial.println(mqttClient.state());
  }
}

// ===================== Analytics =====================
void updateHeatmap(float dt_s, float signedSpeed_mps, float yawRate_rad_s) {
  yaw_rad += yawRate_rad_s * dt_s;

  posX_m += signedSpeed_mps * cosf(yaw_rad) * dt_s;
  posY_m += signedSpeed_mps * sinf(yaw_rad) * dt_s;

  int cx = MAP_W / 2 + (int)floor(posX_m / CELL_M);
  int cy = MAP_H / 2 + (int)floor(posY_m / CELL_M);

  if (cx >= 0 && cx < MAP_W && cy >= 0 && cy < MAP_H) {
    if (occupancy[cy][cx] < 65535) occupancy[cy][cx]++;
    if (absf(signedSpeed_mps) < 0.05f) {
      uint16_t add = (uint16_t)(dt_s * 1000.0f);
      if ((uint32_t)dwellMap[cy][cx] + add > 65535) dwellMap[cy][cx] = 65535;
      else dwellMap[cy][cx] += add;
    }
  }
}

String topHotspotString() {
  int bestX = -1, bestY = -1;
  uint16_t best = 0;

  for (int y = 0; y < MAP_H; y++) {
    for (int x = 0; x < MAP_W; x++) {
      if (dwellMap[y][x] > best) {
        best = dwellMap[y][x];
        bestX = x;
        bestY = y;
      }
    }
  }

  if (bestX < 0) return "N/A";

  char buf[32];
  snprintf(buf, sizeof(buf), "(%d,%d) %ums", bestX, bestY, (unsigned)best);
  return String(buf);
}

void updateAnchorMetrics(int32_t rssiA, int32_t rssiB, int32_t rssiC) {
  M.anchorA_rssi = rssiA;
  M.anchorB_rssi = rssiB;
  M.anchorC_rssi = rssiC;

  M.anchorsSeen = 0;
  if (rssiA > -120) M.anchorsSeen++;
  if (rssiB > -120) M.anchorsSeen++;
  if (rssiC > -120) M.anchorsSeen++;

  M.zone = "UNKNOWN";


  if (rssiA > -120 && rssiB > -120 && abs(rssiA - rssiB) <= 4 && rssiA > rssiC && rssiB > rssiC) {
    M.zone = "BETWEEN_A_B";
  } else if (rssiB > -120 && rssiC > -120 && abs(rssiB - rssiC) <= 4 && rssiB > rssiA && rssiC > rssiA) {
    M.zone = "BETWEEN_B_C";
  } else if (rssiA > -120 && rssiC > -120 && abs(rssiA - rssiC) <= 4 && rssiA > rssiB && rssiC > rssiB) {
    M.zone = "BETWEEN_A_C";
  } else if (rssiA >= rssiB && rssiA >= rssiC && rssiA > -120) {
    M.zone = "ZONE_A";
  } else if (rssiB >= rssiA && rssiB >= rssiC && rssiB > -120) {
    M.zone = "ZONE_B";
  } else if (rssiC >= rssiA && rssiC >= rssiB && rssiC > -120) {
    M.zone = "ZONE_C";
  }
}

void startAnchorScan() {
  if (WiFi.status() != WL_CONNECTED || anchorScanInProgress) return;

  int rc = WiFi.scanComplete();
  if (rc == WIFI_SCAN_RUNNING) {
    anchorScanInProgress = true;
    return;
  }

  if (rc >= 0) {
    WiFi.scanDelete();
  }

  if (WiFi.scanNetworks(true, true) == WIFI_SCAN_FAILED) {
    Serial.println("Anchor scan start failed");
    return;
  }

  anchorScanInProgress = true;
}

void serviceAnchorScan() {
  if (!anchorScanInProgress) return;

  int n = WiFi.scanComplete();
  if (n == WIFI_SCAN_RUNNING || n == WIFI_SCAN_FAILED) return;

  int32_t rssiA = -127;
  int32_t rssiB = -127;
  int32_t rssiC = -127;

  for (int i = 0; i < n; i++) {
    String s = WiFi.SSID(i);
    int32_t r = WiFi.RSSI(i);

    if (s == ANCHOR_A) {
      rssiA = r;
    } else if (s == ANCHOR_B) {
      rssiB = r;
    } else if (s == ANCHOR_C) {
      rssiC = r;
    }
  }

  updateAnchorMetrics(rssiA, rssiB, rssiC);
  WiFi.scanDelete();
  anchorScanInProgress = false;
}

void detectStepCadence(uint32_t nowMs) {
  const uint32_t MIN_STEP_MS = 220;
  const uint32_t MAX_STEP_MS = 1500;
  const float MIN_THRESH = 0.055f;

  static float fast = 0.0f;
  static float slow = 0.0f;
  static float noiseFloor = 0.0f;
  static bool stepArmed = true;
  static float peakSignal = 0.0f;
  static uint32_t peakTimeMs = 0;

  fast = ema(fast, M.aDyn, 0.55f);
  slow = ema(slow, M.aDyn, 0.03f);

  float signal = fast - slow;
  if (signal < 0.0f) signal = 0.0f;
  adynFilt_dbg = signal;

  noiseFloor = ema(noiseFloor, signal, 0.02f);
  float riseThresh = noiseFloor * 1.55f + 0.025f;
  if (riseThresh < MIN_THRESH) riseThresh = MIN_THRESH;
  float fallThresh = riseThresh * 0.55f;

  if (stepArmed) {
    if (signal >= riseThresh && (lastStepPeakMs == 0 || nowMs - lastStepPeakMs >= MIN_STEP_MS)) {
      stepArmed = false;
      peakSignal = signal;
      peakTimeMs = nowMs;
    }
  } else {
    if (signal > peakSignal) {
      peakSignal = signal;
      peakTimeMs = nowMs;
    }

    if (signal <= fallThresh) {
      if (lastStepPeakMs != 0) {
        uint32_t dt = peakTimeMs - lastStepPeakMs;
        if (dt >= MIN_STEP_MS && dt <= MAX_STEP_MS) {
          float spm = 60000.0f / (float)dt;
          cadenceEMA_spm = (cadenceEMA_spm == 0.0f) ? spm : ema(cadenceEMA_spm, spm, 0.35f);
        }
      }

      lastStepPeakMs = peakTimeMs;
      stepArmed = true;
      peakSignal = 0.0f;
    }
  }

  if (lastStepPeakMs != 0) {
    uint32_t idleMs = nowMs - lastStepPeakMs;
    if (idleMs > MAX_STEP_MS) {
      cadenceEMA_spm *= 0.92f;
      if (idleMs > MAX_STEP_MS * 2 || cadenceEMA_spm < 3.0f) {
        cadenceEMA_spm = 0.0f;
      }
    }
  }

  M.stepCadence_spm = cadenceEMA_spm;
}

void detectPickupDrop(uint32_t nowMs) {
  static float lastPitch = 0, lastRoll = 0;
  float dTilt = absf(M.pitchDeg - lastPitch) + absf(M.rollDeg - lastRoll);
  lastPitch = M.pitchDeg;
  lastRoll = M.rollDeg;

  M.pickup = false;
  M.dropdown = false;

  bool accelSpike = M.aDyn > pickupAccelThreshold;
  bool impactSpike = M.aDyn > dropImpactThreshold;
  bool nearStationaryWheel = M.speed_mps < 0.03f;

  if (!isLifted && nearStationaryWheel && accelSpike && dTilt > 8.0f) {
    isLifted = true;
    lastPickupMs = nowMs;
    M.pickup = true;
    actuatorOnFor(200);
  }

  if (isLifted && impactSpike && (nowMs - lastPickupMs > 150)) {
    isLifted = false;
    M.dropdown = true;
    actuatorOnFor(200);
  }
}

void updateDwell(uint32_t nowMs) {
  bool stationary = (M.speed_mps < 0.03f && M.aDyn < 0.35f);

  if (stationary) {
    if (!inDwell) {
      inDwell = true;
      dwellStartMs = nowMs;
    }
    M.dwell_ms = nowMs - dwellStartMs;
  } else {
    inDwell = false;
    M.dwell_ms = 0;
  }

  if (M.dwell_ms > dwellAlertThreshold) {
    actuatorOnFor(150);
  }
}

void classifyCarryStyle() {
  if (isLifted) {
    M.carryStyle = "LIFTED";
    return;
  }

  if (M.speed_mps < 0.02f && M.aDyn < 0.25f) {
    M.carryStyle = "PARKED";
    return;
  }

  float tilt = max(absf(M.pitchDeg), absf(M.rollDeg));
  if (tilt > 18.0f && M.speed_mps > 0.05f) M.carryStyle = "TILTED_PUSH";
  else if (dynRms > 0.9f) M.carryStyle = "ROUGH_ROLL";
  else M.carryStyle = "SMOOTH_ROLL";
}

void classifyLoadProxy() {
  float score = 0.0f;
  score += (0.8f - clampf(vibEMA, 0, 0.8f));
  score += (0.6f - clampf(jerkEMA, 0, 0.6f));
  score += (M.speed_mps > 0.05f ? 0.2f : 0.0f);

  if (isLifted) M.loadProxy = "UNKNOWN";
  else if (score > 0.7f) M.loadProxy = "HEAVY_PROXY";
  else if (score > 0.2f) M.loadProxy = "MEDIUM_PROXY";
  else M.loadProxy = "LIGHT_PROXY";
}

void classifyBrowsingAndQueue(uint32_t nowMs) {
  bool lowMedSpeed = (M.speed_mps > 0.03f && M.speed_mps < 0.6f);

  if (nowMs - lastStopGoMarkMs > 500) {
    lastStopGoMarkMs = nowMs;
    uint8_t mark = (M.speed_mps < 0.05f) ? 1 : 2;
    stopGoHistory[stopGoIdx] = mark;
    stopGoIdx = (stopGoIdx + 1) % STOPGO_BUF;
  }

  int transitions = 0;
  for (int i = 1; i < STOPGO_BUF; i++) {
    if (stopGoHistory[i] != 0 && stopGoHistory[i - 1] != 0 && stopGoHistory[i] != stopGoHistory[i - 1]) {
      transitions++;
    }
  }

  bool frequentTurns = turnRateEMA > 15.0f;
  bool stopStart = (transitions >= 4);
  M.browsing = (lowMedSpeed && (frequentTurns || stopStart || M.dwell_ms > 2000));

  bool creep = (M.speed_mps > 0.01f && M.speed_mps < 0.20f);
  bool lowTurn = (turnRateEMA < 7.0f);

  int stopCount = 0;
  for (int i = 0; i < STOPGO_BUF; i++) {
    if (stopGoHistory[i] == 1) stopCount++;
  }

  bool shortStops = (stopCount > 6 && transitions >= 3);
  M.queueDetect = ((creep || M.dwell_ms > queueDwellThreshold) && lowTurn && shortStops);

  if (M.queueDetect) {
    actuatorOnFor(300);
  }
}

const char* carryLabel() {
  if (M.carryStyle == "LIFTED") return "Lifted";
  if (M.carryStyle == "PARKED") return "Paused";
  if (M.carryStyle == "TILTED_PUSH") return "Moving";
  if (M.carryStyle == "ROUGH_ROLL") return "Rolling";
  if (M.carryStyle == "SMOOTH_ROLL") return "Gliding";
  return "Active";
}

const char* loadLabel() {
  if (M.loadProxy == "HEAVY_PROXY") return "Heavy";
  if (M.loadProxy == "MEDIUM_PROXY") return "Medium";
  if (M.loadProxy == "LIGHT_PROXY") return "Light";
  return "Unknown";
}

const char* zoneLabel() {
  if (M.zone == "ZONE_A") return "A";
  if (M.zone == "ZONE_B") return "B";
  if (M.zone == "ZONE_C") return "C";
  if (M.zone == "BETWEEN_A_B") return "A-B";
  if (M.zone == "BETWEEN_B_C") return "B-C";
  if (M.zone == "BETWEEN_A_C") return "A-C";
  return "--";
}

const char* modeLabel() {
  if (M.queueDetect) return "Queue";
  if (M.browsing) return "Browse";
  if (M.carryStyle == "PARKED") return "Pause";
  return "Shop";
}

const char* heroMessage() {
  if (M.queueDetect) return "Queue ahead";
  if (M.browsing) return "Keep browsing";
  if (M.pickup) return "Basket lifted";
  if (M.dropdown) return "Set down gently";
  if (M.stepCadence_spm > 20.0f || M.speed_mps > 0.05f) return "On the move";
  if (M.carryStyle == "LIFTED") return "Hold steady";
  if (M.carryStyle == "PARKED") return "Ready to shop";
  return "Cartly ready";
}

uint16_t heroColor() {
  if (M.queueDetect) return C_RED;
  if (M.browsing) return C_ORANGE;
  if (M.carryStyle == "LIFTED") return C_YELLOW;
  if (M.stepCadence_spm > 0.0f) return C_GREEN;
  return C_CYAN;
}

void drawStatCard(int16_t x, int16_t y, int16_t w, int16_t h, const char *label, const String &value, uint16_t accent) {
  gfx->fillRoundRect(x, y, w, h, 10, 0x1082);
  gfx->drawRoundRect(x, y, w, h, 10, 0x2945);
  gfx->fillRoundRect(x + 6, y + 8, 4, h - 16, 2, accent);
  gfx->setTextColor(C_GREY);
  gfx->setTextSize(1);
  gfx->setCursor(x + 16, y + 7);
  gfx->print(label);
  gfx->setTextColor(C_WHITE);
  uint8_t valueSize = (w <= 70 || value.length() >= 5) ? 1 : 2;
  gfx->setTextSize(valueSize);
  gfx->setCursor(x + 16, valueSize == 2 ? (y + 21) : (y + 24));
  gfx->print(value);
}

// ===================== UI / Output =====================
void updateDisplay() {
  static bool layoutDrawn = false;
  static String lastHero = "";
  static String stableHero = "";
  static uint32_t stableHeroSinceMs = 0;
  static bool lastLive = false;
  static int lastCadence = -1;
  static int lastCadenceBar = -1;
  static String lastSpeed = "";
  static String lastCarry = "";
  static String lastLoad = "";
  static String lastPause = "";
  static String lastZone = "";
  static String lastMode = "";

  if (displayNeedsFullRedraw) {
    layoutDrawn = false;
    lastHero = "";
    stableHero = "";
    stableHeroSinceMs = 0;
    lastLive = false;
    lastCadence = -1;
    lastCadenceBar = -1;
    lastSpeed = "";
    lastCarry = "";
    lastLoad = "";
    lastPause = "";
    lastZone = "";
    lastMode = "";
    displayNeedsFullRedraw = false;
  }

  if (displayFlashActive) {
    bool invert = ((millis() / 180UL) % 2UL) == 0UL;
    uint16_t bg = invert ? C_RED : C_WHITE;
    uint16_t fg = invert ? C_WHITE : C_RED;

    gfx->fillScreen(bg);
    gfx->setTextColor(fg);
    gfx->setTextSize(2);
    gfx->setCursor(54, 72);
    gfx->print("ATTENTION");
    gfx->setTextSize(1);
    gfx->setCursor(44, 112);
    gfx->print("Please check your trolley");
    gfx->setCursor(56, 132);
    gfx->print("Store staff alerted");
    return;
  }

  uint16_t accent = heroColor();
  int cadenceBar = (int)clampf((M.stepCadence_spm / 130.0f) * 204.0f, 0.0f, 204.0f);
  String heroCandidate = heroMessage();
  bool live = mqttClient.connected();
  int cadence = (int)(M.stepCadence_spm + 0.5f);
  String speedText = String(M.speed_mps, 2);
  String dwellText = String((unsigned long)(M.dwell_ms / 1000UL)) + "s";
  String carryText = carryLabel();
  String loadText = loadLabel();
  String zoneText = zoneLabel();
  String modeText = modeLabel();

  if (stableHero.length() == 0) {
    stableHero = heroCandidate;
    stableHeroSinceMs = millis();
  } else if (heroCandidate != stableHero) {
    bool urgentHero = (heroCandidate == "Queue ahead" || heroCandidate == "Basket lifted" || heroCandidate == "Set down gently");
    if (urgentHero || (millis() - stableHeroSinceMs) > 1200) {
      stableHero = heroCandidate;
      stableHeroSinceMs = millis();
    }
  }

  if (!layoutDrawn) {
    gfx->fillScreen(C_BLACK);
    gfx->fillRoundRect(8, 8, 224, 54, 16, 0x0410);
    gfx->fillRoundRect(12, 12, 216, 46, 14, C_BLACK);
    gfx->drawRoundRect(12, 12, 216, 46, 14, 0x2104);

    gfx->setTextColor(C_GREY);
    gfx->setTextSize(1);
    gfx->setCursor(26, 16);
    gfx->print("CARTLY");

    gfx->setTextColor(C_GREY);
    gfx->setTextSize(1);
    gfx->setCursor(14, 72);
    gfx->print("PACE");
    gfx->setCursor(144, 72);
    gfx->print("MOVE");

    gfx->drawRoundRect(14, 112, 212, 16, 8, 0x2945);

    layoutDrawn = true;
  }

  gfx->fillRect(12, 12, 8, 46, accent);

  if (stableHero != lastHero) {
    gfx->fillRect(24, 28, 142, 22, C_BLACK);
    gfx->setTextColor(accent);
    gfx->setTextSize(2);
    gfx->setCursor(26, 30);
    gfx->print(stableHero);
    lastHero = stableHero;
  }

  if (live != lastLive) {
    gfx->fillRoundRect(170, 16, 52, 18, 9, live ? C_GREEN : C_RED);
    gfx->setTextColor(C_BLACK);
    gfx->setTextSize(1);
    gfx->setCursor(live ? 180 : 184, 22);
    gfx->print(live ? "LIVE" : "OFF");
    lastLive = live;
  }

  if (cadence != lastCadence) {
    gfx->fillRect(14, 84, 74, 24, C_BLACK);
    gfx->setTextColor(C_WHITE);
    gfx->setTextSize(3);
    gfx->setCursor(14, 84);
    gfx->print(cadence);
    gfx->setTextSize(1);
    gfx->setCursor(92, 97);
    gfx->setTextColor(C_GREY);
    gfx->print("spm");
    lastCadence = cadence;
  }

  if (speedText != lastSpeed) {
    gfx->fillRect(144, 84, 70, 22, C_BLACK);
    gfx->setTextColor(C_CYAN);
    gfx->setTextSize(2);
    gfx->setCursor(144, 84);
    gfx->print(speedText);
    gfx->setTextSize(1);
    gfx->setTextColor(C_GREY);
    gfx->setCursor(144, 104);
    gfx->print("m/s");
    lastSpeed = speedText;
  }

  if (cadenceBar != lastCadenceBar) {
    gfx->fillRoundRect(18, 116, 204, 8, 4, 0x18C3);
    if (cadenceBar > 0) {
      gfx->fillRoundRect(18, 116, cadenceBar, 8, 4, accent);
    }
    lastCadenceBar = cadenceBar;
  }

  if (carryText != lastCarry) {
    drawStatCard(12, 138, 104, 42, "Carry", carryText, C_GREEN);
    lastCarry = carryText;
  }
  if (loadText != lastLoad) {
    drawStatCard(124, 138, 104, 42, "Load", loadText, C_YELLOW);
    lastLoad = loadText;
  }
  if (dwellText != lastPause) {
    drawStatCard(12, 188, 68, 42, "Pause", dwellText, C_ORANGE);
    lastPause = dwellText;
  }
  if (zoneText != lastZone) {
    drawStatCard(86, 188, 68, 42, "Zone", zoneText, C_CYAN);
    lastZone = zoneText;
  }
  if (modeText != lastMode) {
    drawStatCard(160, 188, 68, 42, "Mode", modeText, accent);
    lastMode = modeText;
  }
}

void printSerialSummary(float signedSpeed_mps) {
  Serial.print("{");
  Serial.print("\"timestamp_ms\":"); Serial.print(millis()); Serial.print(",");
  Serial.print("\"device_id\":\""); Serial.print(DEVICE_ID); Serial.print("\",");
  Serial.print("\"step_cadence_spm\":"); Serial.print(M.stepCadence_spm, 1); Serial.print(",");
  Serial.print("\"pickup\":"); Serial.print(M.pickup ? "true" : "false"); Serial.print(",");
  Serial.print("\"drop_down\":"); Serial.print(M.dropdown ? "true" : "false"); Serial.print(",");
  Serial.print("\"dwell_time_ms\":"); Serial.print(M.dwell_ms); Serial.print(",");
  Serial.print("\"carry_style\":\""); Serial.print(M.carryStyle); Serial.print("\",");
  Serial.print("\"load_proxy\":\""); Serial.print(M.loadProxy); Serial.print("\",");
  Serial.print("\"browsing\":"); Serial.print(M.browsing ? "true" : "false"); Serial.print(",");
  Serial.print("\"queue_detect\":"); Serial.print(M.queueDetect ? "true" : "false"); Serial.print(",");
  Serial.print("\"anchor_a_rssi\":"); Serial.print(M.anchorA_rssi); Serial.print(",");
  Serial.print("\"anchor_b_rssi\":"); Serial.print(M.anchorB_rssi); Serial.print(",");
  Serial.print("\"anchor_c_rssi\":"); Serial.print(M.anchorC_rssi); Serial.print(",");
  Serial.print("\"anchors_seen\":"); Serial.print(M.anchorsSeen); Serial.print(",");
  Serial.print("\"zone\":\""); Serial.print(M.zone); Serial.print("\",");
  Serial.print("\"imu_ok\":"); Serial.print(M.imuOk ? "true" : "false"); Serial.print(",");
  Serial.print("\"aws_ok\":"); Serial.print(M.awsOk ? "true" : "false"); Serial.print(",");
  Serial.print("\"system_state\":\""); Serial.print(M.systemState); Serial.print("\",");
  Serial.print("\"transport\":\""); Serial.print(directStreamReady() ? "direct" : "mqtt"); Serial.print("\",");
  Serial.print("\"speed_mps\":"); Serial.print(M.speed_mps, 3); Serial.print(",");
  Serial.print("\"signed_speed_mps\":"); Serial.print(signedSpeed_mps, 3); Serial.print(",");
  Serial.print("\"distance_m\":"); Serial.print(M.dist_m, 2); Serial.print(",");
  Serial.print("\"pos_x_m\":"); Serial.print(posX_m, 2); Serial.print(",");
  Serial.print("\"pos_y_m\":"); Serial.print(posY_m, 2); Serial.print(",");
  Serial.print("\"live_hotspot\":\""); Serial.print(M.hotspot); Serial.print("\"");
  Serial.println("}");
}

static void buildPayload(char* buf, size_t sz, float signedSpeed_mps) {
  snprintf(
    buf, sz,
    "{"
    "\"timestamp_ms\":%lu,"
    "\"device_id\":\"%s\","
    "\"step_cadence_spm\":%.1f,"
    "\"pickup\":%s,"
    "\"drop_down\":%s,"
    "\"dwell_time_ms\":%lu,"
    "\"carry_style\":\"%s\","
    "\"load_proxy\":\"%s\","
    "\"browsing\":%s,"
    "\"queue_detect\":%s,"
    "\"anchor_a_rssi\":%ld,"
    "\"anchor_b_rssi\":%ld,"
    "\"anchor_c_rssi\":%ld,"
    "\"anchors_seen\":%u,"
    "\"zone\":\"%s\","
    "\"imu_ok\":%s,"
    "\"aws_ok\":%s,"
    "\"system_state\":\"%s\","
    "\"transport\":\"%s\","
    "\"speed_mps\":%.3f,"
    "\"signed_speed_mps\":%.3f,"
    "\"distance_m\":%.2f,"
    "\"pos_x_m\":%.2f,"
    "\"pos_y_m\":%.2f,"
    "\"live_hotspot\":\"%s\""
    "}",
    (unsigned long)millis(),
    DEVICE_ID,
    M.stepCadence_spm,
    M.pickup ? "true" : "false",
    M.dropdown ? "true" : "false",
    (unsigned long)M.dwell_ms,
    M.carryStyle.c_str(),
    M.loadProxy.c_str(),
    M.browsing ? "true" : "false",
    M.queueDetect ? "true" : "false",
    (long)M.anchorA_rssi,
    (long)M.anchorB_rssi,
    (long)M.anchorC_rssi,
    M.anchorsSeen,
    M.zone.c_str(),
    M.imuOk ? "true" : "false",
    M.awsOk ? "true" : "false",
    M.systemState.c_str(),
    directStreamReady() ? "direct" : "mqtt",
    M.speed_mps,
    signedSpeed_mps,
    M.dist_m,
    posX_m,
    posY_m,
    M.hotspot.c_str()
  );
}

bool directStreamReady() {
  return directEnabled && directHost[0] != '\0' && WiFi.status() == WL_CONNECTED;
}

void publishTelemetry(float signedSpeed_mps) {
  if (directStreamReady()) return;
  if (!mqttClient.connected()) return;
  char payload[1200];
  buildPayload(payload, sizeof(payload), signedSpeed_mps);
  bool ok = mqttClient.publish(MQTT_TOPIC_PUB, payload);
  if (!ok) {
    mqttClient.disconnect();
    lastMQTTAttemptMs = 0;
  }
}

void streamDirect(float signedSpeed_mps) {
  if (!directStreamReady()) return;
  char payload[1200];
  buildPayload(payload, sizeof(payload), signedSpeed_mps);
  if (directUdp.beginPacket(directHost, directPort)) {
    directUdp.write((uint8_t*)payload, strlen(payload));
    directUdp.endPacket();
  }
}

// ===================== Setup / Loop =====================
void setup() {
  initMetrics();

  Serial.begin(115200);
  delay(300);

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);

  pinMode(PIN_LCD_BL, OUTPUT);
  digitalWrite(PIN_LCD_BL, HIGH);

  pinMode(PIN_ACTUATOR, OUTPUT);
  digitalWrite(PIN_ACTUATOR, LOW);

  gfx->begin();
  gfx->fillScreen(C_BLACK);
  gfx->setTextWrap(false);
  gfx->setTextColor(C_WHITE);
  gfx->setTextSize(2);
  gfx->setCursor(8, 8);
  gfx->println("Smart Trolley");
  gfx->setTextSize(1);
  gfx->println("AWS IoT Demo");

  Wire.begin(PIN_IMU_SDA, PIN_IMU_SCL);
  Wire.setClock(400000);

  if (!imu.begin()) fatal("QMI8658 init failed");

  imu.setAccelUnit_mg(false);
  imu.setGyroUnit_dps(true);
  imu.setDisplayPrecision(3);

  pinMode(PIN_ENC_A, INPUT);
  pinMode(PIN_ENC_B, INPUT);
  delay(10);

  prevAB = ((uint8_t)digitalRead(PIN_ENC_A) << 1) | (uint8_t)digitalRead(PIN_ENC_B);

  memset(occupancy, 0, sizeof(occupancy));
  memset(dwellMap, 0, sizeof(dwellMap));
  memset(stopGoHistory, 0, sizeof(stopGoHistory));

  uint32_t now = millis();
  connectWiFi(now);
  connectMQTT(now);

  gfx->setTextColor(C_GREEN);
  gfx->setCursor(8, 26);
  gfx->println("Ready");

  lastLoopMs = now;
}

void loop() {
  uint32_t now = millis();

  connectWiFi(now);
  connectMQTT(now);
  mqttClient.loop();
  serviceActuator();
  serviceDisplayFlash();
  serviceAnchorScan();
  pollEncoderFast();

  if (now - lastLoopMs < LOOP_MS) return;

  float dt_s = (now - lastLoopMs) / 1000.0f;
  lastLoopMs = now;

  QMI8658_Data d;
  bool imuOk = imu.readSensorData(d);
  M.imuOk = imuOk;

  if (imuOk) {
    M.ax = d.accelX;
    M.ay = d.accelY;
    M.az = d.accelZ;
    M.gx = d.gyroX;
    M.gy = d.gyroY;
    M.gz = d.gyroZ;
  }

  static long lastEnc = 0;
  long enc;
  uint32_t pollHits;
  enc = encoderCount;
  pollHits = encoderPollHits;

  uint8_t rawA = (uint8_t)digitalRead(PIN_ENC_A);
  uint8_t rawB = (uint8_t)digitalRead(PIN_ENC_B);

  Serial.print("[ENC] A="); Serial.print(rawA);
  Serial.print(" B=");       Serial.print(rawB);
  Serial.print(" count=");   Serial.print(enc);
  Serial.print(" pollHits="); Serial.print(pollHits);
  Serial.print(" isrHits="); Serial.println(encIsrHits);

  long dEnc = enc - lastEnc;
  lastEnc = enc;

  float dMeters = countsToMeters(dEnc);
  M.dist_m += fabs(dMeters);

  float instSpeedSigned = (dt_s > 0.001f) ? (dMeters / dt_s) : 0.0f;
  float instSpeedAbs = (dt_s > 0.001f) ? (fabs(dMeters) / dt_s) : 0.0f;
  speedSignedSmooth = ema(speedSignedSmooth, instSpeedSigned, 0.35f);
  speedAbsSmooth = ema(speedAbsSmooth, instSpeedAbs, 0.35f);
  float signedSpeed_mps = speedSignedSmooth;

  M.speed_mps = speedAbsSmooth;

  M.aMag = sqrtf(M.ax * M.ax + M.ay * M.ay + M.az * M.az);

  gravX = ema(gravX, M.ax, 0.04f);
  gravY = ema(gravY, M.ay, 0.04f);
  gravZ = ema(gravZ, M.az, 0.04f);

  float dx = M.ax - gravX;
  float dy = M.ay - gravY;
  float dz = M.az - gravZ;
  M.aDyn = sqrtf(dx * dx + dy * dy + dz * dz);

  dynRms = sqrtf(ema(dynRms * dynRms, M.aDyn * M.aDyn, 0.15f));
  vibEMA = ema(vibEMA, M.aDyn, 0.1f);

  float jerk = (dt_s > 0.001f) ? absf((M.speed_mps - lastSpeedMps) / dt_s) : 0.0f;
  lastSpeedMps = M.speed_mps;
  jerkEMA = ema(jerkEMA, clampf(jerk, 0, 2.0f), 0.1f);

  M.pitchDeg = atan2f(-M.ax, sqrtf(M.ay * M.ay + M.az * M.az)) * 57.2958f;
  M.rollDeg  = atan2f(M.ay, M.az) * 57.2958f;

  turnRateEMA = ema(turnRateEMA, absf(M.gz), 0.15f);
  speedVarEMA = ema(speedVarEMA, absf(M.speed_mps - lastSpeedForVar), 0.2f);
  lastSpeedForVar = M.speed_mps;

  detectStepCadence(now);
  detectPickupDrop(now);
  updateDwell(now);
  classifyCarryStyle();
  classifyLoadProxy();
  classifyBrowsingAndQueue(now);

  // Wi-Fi scans can stall timing-sensitive encoder sampling, so only scan
  // when the trolley is effectively stationary.
  if (now - lastRssiScanMs >= rssiScanIntervalMs && M.speed_mps < 0.02f) {
    lastRssiScanMs = now;
    startAnchorScan();
  }

  updateHeatmap(dt_s, signedSpeed_mps, M.gz * 0.0174533f);
  M.hotspot = topHotspotString();

  updateSystemState();

  if (now - lastSerialMs >= SERIAL_PERIOD_MS) {
    lastSerialMs = now;
    printSerialSummary(signedSpeed_mps);
  }

  if (now - lastDisplayMs >= DISPLAY_PERIOD_MS) {
    lastDisplayMs = now;
    updateDisplay();
  }

  if (now - lastDirectUploadMs >= DIRECT_UPLOAD_MS) {
    lastDirectUploadMs = now;
    streamDirect(signedSpeed_mps);
  }

  if (now - lastCloudUploadMs >= CLOUD_UPLOAD_MS) {
    lastCloudUploadMs = now;
    publishTelemetry(signedSpeed_mps);
  }

  M.pickup = false;
  M.dropdown = false;
}
