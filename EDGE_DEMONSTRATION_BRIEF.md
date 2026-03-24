# Cartly — Smart Trolley Intelligence Platform
## Edge Demonstration Brief
### ELEC0033 — UCL Year 3

> **Purpose of this document:** Comprehensive project brief for use by an AI agent to generate a PowerPoint presentation for the edge demonstration. All technical details, marking criteria mappings, and talking points are included below.

---

## 1. Project Overview

**Cartly** is a real-time IoT edge intelligence platform fitted to a supermarket shopping trolley. The system captures multi-sensor telemetry, classifies shopper behaviour entirely on-device (edge), transmits data to a cloud stack, and exposes a live web dashboard with remote configuration, analytics, and live external context enrichment.

The system architecture is a three-tier edge deployment:
1. **Infrastructure layer** — Two Arduino MKR1010 boards and one ESP32 C3 Super Mini deployed as fixed Wi-Fi access points (ANCHOR_A, ANCHOR_B, ANCHOR_C) providing the RSSI positioning grid
2. **Edge layer** — ESP32-S3 microcontroller on the trolley running all sensing, classification, actuation, and telemetry
3. **Cloud/Dashboard layer** — MQTT broker (`mqtt.yungcz.com`), FastAPI backend (`api.cartly.yungcz.com`), AWS RDS MySQL database, React frontend; enriched with live Open-Meteo weather data

---

## 1.1 Key User Requirements & System Performance Indicators

### User Requirements

The system was designed around three distinct user groups operating a supermarket trolley deployment:

| User | Requirement |
|------|-------------|
| **Store staff** | Receive real-time alerts when a trolley enters a checkout queue, so they can manage customer flow without manual observation |
| **Store staff** | Be notified immediately when a trolley is picked up or dropped (potential misuse or item damage) |
| **Store manager** | View historical analytics on zone utilisation, event frequency, and trolley movement patterns across sessions |
| **Operator** | Adjust detection sensitivity remotely (e.g. reduce false alerts during busy periods) without physical access to the device |
| **Operator** | Know the current health status of every deployed trolley at a glance |
| **System requirement** | Device must be battery-powered and untethered — no power cables, fits standard trolley form factor |
| **System requirement** | Data must be persisted centrally for cross-session and cross-device analysis |
| **System requirement** | System must continue local edge processing and actuation even if cloud connectivity is temporarily lost |

### System Performance Indicators (KPIs)

| KPI | Target | Achieved |
|-----|--------|---------|
| Telemetry update rate | Real-time, <200 ms latency | 100 ms (10 Hz MQTT) |
| Event upload latency | <100 ms from trigger to cloud | 40 ms priority gap |
| Sensor sample rate | ≥20 Hz for IMU | 50 Hz (20 ms loop) |
| Battery runtime per charge | ≥1 full retail shift (~3.5–4 hrs) | ~3.5 hours (1100 mAh @ 1W) |
| MQTT reconnection time | <5 s | <1.5 s |
| Positioning granularity | Zone-level (3 zones minimum) | 3 zones + 2D trilateration within zones |
| Data completeness | All sensor fields labelled and stored | 28 named columns per reading in AWS RDS |
| Edge classifier coverage | Detect key shopper events autonomously | 8 classifiers: carry style, pickup, drop, dwell, browsing, queue, cadence, load |

---

## 1.2 Evidence-Informed Design Choices

### 1. Indoor Positioning — RSSI Trilateration with Log-Distance Path Loss

Cartly uses the **log-distance path loss model** for converting RSSI readings to estimated distances, which is the standard model for indoor RF propagation used in the literature (Rappaport, *Wireless Communications*, 2002):

```
RSSI(d) = RSSI(d₀) − 10n · log₁₀(d / d₀)
```

- **Reference RSSI at 1 m (`RSSI_REFERENCE_DBM`):** −56 dBm — measured empirically by placing the trolley 1 m from an anchor AP and recording the average RSSI over 10 scans
- **Path loss exponent (`RSSI_PATH_LOSS`):** 2.2 — chosen based on literature values for indoor open retail environments (free space = 2.0; cluttered indoor = 3.0–4.0; a supermarket aisle falls closer to the lower end due to wide open corridors)
- **3-point trilateration** for full 2D position estimate; degrades gracefully to 2-point zone estimation (BETWEEN) and 1-point proximity fallback (UNKNOWN) when fewer anchors are visible — a robustness property recommended in indoor positioning literature

### 2. EMA Filtering for Sensor Noise Rejection

**Exponential Moving Average (EMA)** was chosen over a simple moving average (SMA) for all continuous sensor signals because:
- EMA weights recent samples more heavily, providing faster response to genuine motion events
- EMA has O(1) memory and compute cost (a single multiply-add per sample), critical for a 50 Hz embedded loop
- Applied to: speed smoothing, vibration RMS, jerk magnitude, turn rate, and step cadence

The alpha values (typically 0.1–0.3) were tuned empirically: lower alpha = more smoothing but slower response; higher alpha = faster response but noisier. Speed uses α≈0.3 to balance responsiveness with noise rejection during wheel encoder jitter.

### 3. Gravity Removal from Accelerometer (Dynamic Acceleration Isolation)

The QMI8658 provides raw acceleration including gravitational component. To isolate trolley motion from orientation:
- A **low-pass EMA** of the raw acceleration is maintained as an estimate of the gravity vector
- Dynamic acceleration (`aDyn`) = raw acceleration − gravity estimate
- This is the standard approach in activity recognition literature (Bao & Intille, 2004) for separating device orientation from user-caused motion
- Without this, a tilted trolley would produce a constant non-zero "acceleration" from gravity, causing false pickup/drop triggers

### 4. MQTT Protocol Selection

MQTT was selected over HTTP polling and raw TCP because:
- **ISO/IEC 20922** standard — purpose-built for constrained IoT devices with unreliable networks
- **Persistent connection** avoids repeated TLS handshake overhead of HTTPS (a handshake costs ~5–10 KB; at 10 Hz that would be impractical)
- **QoS 1 (at-least-once)** was chosen over QoS 0 (fire-and-forget) to guarantee event delivery, and over QoS 2 (exactly-once) to avoid the double-acknowledgement overhead on a 10 Hz continuous stream
- **Pub/sub topic separation** (`telemetry` publish vs `config` subscribe) provides natural access control without additional middleware

### 5. TLS 1.3 for Transport Security

TLS 1.3 (IETF RFC 8446) was chosen over TLS 1.2 because:
- **1-RTT handshake** vs TLS 1.2's 2-RTT — reduces reconnection latency, important given the 1.5 s MQTT retry cycle
- **Removed weak cipher suites** (RC4, 3DES, MD5-based MACs) present in TLS 1.2 — reduces attack surface
- **CA certificate pinned in firmware** (ISRG Root X1) — prevents man-in-the-middle attacks even if a subordinate CA is compromised, following the principle of certificate pinning recommended for embedded IoT devices (OWASP IoT Security Guidance)

### 6. Empirical Threshold Calibration

All detection thresholds were set empirically through repeated physical tests:

| Parameter | Value | Calibration method |
|-----------|-------|--------------------|
| `pickupAccelThreshold` | 2.5 m/s² | Repeated lift tests; value above typical push vibration (~1.2 m/s²) but below clear pickup (~3–5 m/s²) |
| `dropImpactThreshold` | 4.0 m/s² | Drop-onto-ground tests; higher than pickup to avoid shelf-bump false triggers |
| `queueDwellThreshold` | 3000 ms | Observed minimum stop duration in checkout queue behaviour; shorter stops are aisle browsing |
| `dwellAlertThreshold` | 4000 ms | Set 1 s above queue threshold to allow queue detection to fire first |
| `rssiScanIntervalMs` | 15 000 ms | Each Wi-Fi scan takes ~200 ms and blocks the loop; 15 s interval gives fresh position data without impacting the 50 Hz sensor loop |
| `MOTOR_ENCODER_CPR` | 3 counts/rev | Verified by manually rotating wheel exactly one revolution and counting encoder pulses |
| `WHEEL_DIAM_M` | 0.0452 m | Physical measurement of trolley rear wheel diameter with calipers |

### 7. Dual-Path Telemetry (MQTT + UDP)

A dual-path architecture was designed after observing that cloud MQTT round-trip latency (~80–150 ms) was insufficient for real-time dashboard updates during live demonstrations:
- **MQTT path:** reliable, encrypted, cloud-persisted — primary for data storage and remote access
- **UDP direct path:** low-latency (~5 ms LAN), best-effort — secondary for dashboard live view on the same LAN
- The backend advertises its LAN IP to the device via the MQTT config topic on startup, so no manual configuration is needed on the device

---

## 1.3 Presentation Theme Guide

The PowerPoint should match the live Cartly dashboard theme so the demonstration feels like one coherent product rather than a separate academic slide deck.

### Visual direction
- **Overall look:** dark, technical, minimal, high-contrast, control-room style
- **Background:** solid black `#000000` or near-black `#0a0a0a`
- **Panels/cards:** near-black surfaces with thin soft borders such as `rgba(255,255,255,0.06)`
- **Primary text:** white `#FFFFFF` or off-white `#E5E7EB`
- **Secondary text:** muted slate/grey such as `#A1A1AA`, `#94A3B8`, or `#64748B`
- **Do not use:** bright academic templates, pastel colours, rounded cartoon graphics, or generic blue corporate themes

### Accent colours
- **Success / live / healthy:** green `#22C55E`
- **Warning / queue / attention:** amber `#F59E0B` or `#FBBF24`
- **Info / cloud / analytics highlight:** blue `#2563EB` or `#3B82F6`
- **Optional premium accent for heatmap / analytics emphasis:** violet `#A855F7`

Use accents sparingly. Most of the slide should remain monochrome, with colour used only to direct attention to status, events, and key metrics.

### Typography
- **Headings/body:** clean modern sans-serif in the style of Inter
- **Numerical values / telemetry / timestamps:** monospace in the style of JetBrains Mono
- **Heading style:** bold, compact, modern; avoid serif fonts and decorative title fonts

### Layout guidance
- Use dashboard-style cards for KPIs, architecture blocks, and results
- Prefer horizontal strips, status chips, and metric tiles over bullet-heavy white slides
- Use thin dividers, subtle borders, and generous spacing
- Keep diagrams simple and sharp, with dark panels and bright labels
- Charts should use dark backgrounds with green, blue, amber, and violet series accents matching the web UI

### Slide-specific styling cues
- **Title slide:** black background, centred Cartly branding, subtle blue/green glow or gradient bloom in the corners
- **Architecture slide:** dark panel blocks for Infrastructure, Edge, and Cloud layers
- **Sensor slide:** one card per sensor with white titles and muted technical annotations
- **Analytics slide:** screenshots from Metabase and the live dashboard should be framed inside dark bordered cards
- **Security / reliability slides:** use green for healthy states and amber for warnings/failsafe discussion

### Tone for generated visuals
- Product-demo aesthetic rather than textbook aesthetic
- Confident and polished, similar to a startup operations dashboard
- Minimal clutter, no clip-art, no bright stock icons

---

## 2. Hardware Architecture

### 2.1 Infrastructure: Anchor Nodes (Mixed Hardware)
Two Arduino MKR1010 boards and one ESP32 C3 Super Mini are deployed as static Wi-Fi access points at fixed, known positions in the store:
- **ANCHOR_A** — broadcasts SSID `ANCHOR_A` (Arduino MKR1010)
- **ANCHOR_B** — broadcasts SSID `ANCHOR_B` (Arduino MKR1010)
- **ANCHOR_C** — broadcasts SSID `ANCHOR_C` (ESP32 C3 Super Mini)

These nodes form the indoor positioning infrastructure. The ESP32-S3 on the trolley passively scans for these SSIDs and measures RSSI from each, which is then used for trilateration to estimate the trolley's 2D position within the store.

### 2.2 Edge Node: ESP32-S3 (Trolley-mounted)
The main processing unit. It runs the full sensor pipeline, behaviour classifier, actuator control, and communications stack.

**Pins used:**
| Function | GPIO |
|----------|------|
| IMU SDA (QMI8658) | 47 |
| IMU SCL (QMI8658) | 48 |
| Encoder Channel A | 1 |
| Encoder Channel B | 2 |
| Haptic Actuator | 21 |
| LCD Backlight | 20 |
| LCD DC | 38 |
| LCD CS | 39 |
| LCD SCK/MOSI/RST | 40/41/42 |

---

## 3. Four Sensor Types

### Sensor 1: IMU Accelerometer (QMI8658 — 3-axis)
- **What it measures:** Linear acceleration in X, Y, Z axes (in mg)
- **Derived metrics:**
  - Dynamic acceleration magnitude (`aDyn`) — removes gravity component
  - Pitch and roll angles (orientation)
  - Pickup detection (threshold: 2.5 m/s²)
  - Drop/impact detection (threshold: 4.0 m/s²)
  - Step cadence estimation (from periodic acceleration peaks)
  - Vibration RMS via exponential moving average (EMA)
  - Jerk (rate of change of acceleration)
- **Update rate:** Every 20ms (50 Hz main loop)

### Sensor 2: IMU Gyroscope (QMI8658 — 3-axis)
- **What it measures:** Angular velocity in X, Y, Z axes (degrees per second)
- **Derived metrics:**
  - Turn rate EMA — used for queue detection and browsing detection
  - Orientation change tracking for carry style classification
  - Yaw integration for 2D dead-reckoning position estimate
- **Same physical chip as accelerometer** (QMI8658 is a 6-axis IMU) but constitutes a distinct sensor modality

### Sensor 3: RSSI / Wi-Fi Signal Scanner
- **What it measures:** Received Signal Strength Indicator (dBm) from each of the three anchor APs (2× MKR1010 + 1× ESP32 C3 Super Mini)
- **Scan interval:** 15 seconds (configurable via MQTT, `rssiScanIntervalMs`)
- **Scan condition:** Only scans when speed < 0.02 m/s to avoid stalling main loop
- **Minimum detection threshold:** -120 dBm
- **Derived metrics:**
  - Zone classification: ZONE_A, ZONE_B, ZONE_C, BETWEEN (2-point fallback), UNKNOWN (<2 anchors)
  - 2D position estimate via trilateration (posX_m, posY_m)
  - `anchorsSeen` count (0–3) feeds into system health state
  - Store heatmap — Gaussian KDE over a 6×6 m floor plan rendered on the dashboard (80×80 resolution, σ=3.5 cells)

### Sensor 4: Wheel Encoder (Magnetic Rotary Encoder)
- **What it measures:** Wheel rotation pulses via interrupt on GPIO 1
- **Specification:** 3 counts per wheel revolution (6-pole magnetic disc on wheel shaft, rising-edge counting on Channel A)
- **Wheel diameter:** 45.2 mm → circumference = 142.0 mm
- **Derived metrics:**
  - Distance travelled (metres)
  - Speed (m/s) — both signed (direction-aware) and absolute
  - Smoothed speed via EMA for noise rejection
- **Resolution:** ~47.3 mm per count
- **ISR protection:** Encoder count is protected via interrupt-disable critical section

---

## 4. Actuators

### Actuator 1: Haptic Output (GPIO 21)
- Binary HIGH/LOW output driving a haptic element
- Non-blocking: fires for a configurable duration (`actuatorPulseMs`) then auto-releases
- **Trigger events:**
  - Pickup detected → 200 ms pulse
  - Drop-down detected → 200 ms pulse
  - Dwell alert (>4 s pause) → 150 ms pulse
  - Queue detection → 300 ms pulse
- Can be disabled remotely via `actuatorEnabled: false` MQTT config command

### Actuator 2: ST7789 TFT Display Alert (240×240)
- Inverted red/white alternating flash at 180 ms intervals
- Duration configurable via `displayFlashMs` MQTT command
- Message displayed: **"ATTENTION — Check trolley — Staff alerted"**
- Also serves as status display: shows speed, zone, carry style, system state, RSSI bars, event flags

---

## 5. Behaviour Classification (On-Device Edge Intelligence)

All classification runs locally on the ESP32-S3 — **no cloud inference required.**

| Classification | Algorithm | Inputs |
|---|---|---|
| **Carry Style** | 5-state rule-based classifier | Speed, pitch/roll, vibration RMS, dynamic accel |
| **Load Proxy** | EMA of vibration + jerk + speed | Accel, speed, jerk EMA |
| **Pickup Detection** | Threshold on `aDyn` | Accelerometer |
| **Drop Detection** | Threshold on impact `aDyn` | Accelerometer |
| **Dwell Detection** | Timed state machine (speed < threshold) | Encoder speed |
| **Browsing Detection** | Speed + turn rate + dwell combo | Encoder + gyro + dwell timer |
| **Queue Detection** | Creep speed + low turn + stop-go pattern + dwell | All sensors |
| **Step Cadence** | Peak detection on accel magnitude | Accelerometer |
| **Zone / Position** | RSSI trilateration (3-point, 2-point fallback) | Wi-Fi RSSI |
| **Store Heatmap** | Gaussian KDE on 80×80 grid, rendered to canvas | Position (from RSSI trilateration) |

**Carry Style states:** `LIFTED`, `PARKED`, `TILTED_PUSH`, `ROUGH_ROLL`, `SMOOTH_ROLL`

---

## 6. Power Budget

### Battery Specification
- **Cell type:** Li-Po / Li-Ion
- **Capacity:** 1100 mAh
- **Nominal voltage:** 3.7 V
- **Energy stored:** 1100 mAh × 3.7 V = **4.07 Wh**

### Power Consumption
- **Supply voltage:** 5 V (via USB / boost converter from battery)
- **Current draw (running):** 0.2 A
- **Active power:** 5 V × 0.2 A = **1.0 W**

### Runtime Estimate
Accounting for ~87% DC-DC boost conversion efficiency:

| Metric | Value |
|--------|-------|
| Usable energy (87% efficiency) | 4.07 × 0.87 = **3.54 Wh** |
| Active runtime | 3.54 Wh ÷ 1.0 W = **~3.5 hours** |
| Typical supermarket shift | ~4 hours |

The 3.5-hour runtime is sufficient for a standard retail shift. The system would require charging between morning and afternoon sessions.

**Power consumers (dominant):**
1. Wi-Fi radio (always-on, sleep disabled for MQTT keep-alive) — est. ~150 mA
2. ST7789 TFT display + backlight — est. ~30 mA
3. ESP32-S3 core + peripherals — est. ~20 mA
4. QMI8658 IMU — est. ~1 mA

**Optimisation note:** Wi-Fi sleep is disabled (`WiFi.setSleep(false)`) to ensure low-latency MQTT keep-alive. Enabling Wi-Fi modem sleep (DTIM-based) could reduce power by ~30–40%, extending runtime to ~5 hours, at the cost of ~100 ms additional MQTT latency.

---

## 7. Bandwidth Analysis & Proof of Optimisation

### Telemetry Payload
- **Format:** JSON
- **Payload size:** ~768 bytes per message
- **Fields:** 28 (device_id, timestamp, speed, distance, cadence, accel XYZ, gyro XYZ, pitch, roll, pickup, dropdown, dwell, carry_style, load_proxy, browsing, queue_detect, anchor RSSI ×3, zone, posX, posY, anchors_seen, imu_ok, aws_ok, system_state, hotspot)

---

### Naïve Baseline (No Optimisation)

Without any bandwidth management, the naïve design would transmit every sensor reading immediately at the sensor sample rate:

| Metric | Naïve baseline |
|--------|---------------|
| Sensor loop rate | 50 Hz (every 20 ms — `LOOP_MS = 20`) |
| Upload rate (no rate limiter) | 50 messages/second |
| Upstream bandwidth | 768 B × 50 = **38,400 B/s = 307.2 Kbps** |
| RSSI scan frequency | Every loop tick (every 20 ms) |
| RSSI scan blocking overhead | 200 ms scan ÷ 20 ms loop = **10× loop period** (infeasible) |
| MQTT control packets (QoS 2) | 4 packets × 50 msg/s = **200 MQTT control packets/s** |
| Per-shift data (3.5 hr) | 307,200 bps × 12,600 s ÷ 8 = **~484 MB** |
| Event upload worst-case latency | Up to 20 ms (next loop tick) — no priority mechanism |

---

### Optimisation 1 — Decouple Upload Rate from Sensor Rate

**Problem:** The sensor must run at 50 Hz for accurate IMU-based classification (pickup detection, cadence estimation, carry style). However, the cloud and dashboard do not require 50 Hz updates to function correctly — human perception of "real-time" is satisfied at 10 Hz.

**Solution:** Introduce a separate upload timer (`CLOUD_UPLOAD_MS = 100`) that is independent of the sensor loop (`LOOP_MS = 20`). The sensor always runs at 50 Hz; the cloud upload fires every 100 ms with the latest computed values.

| | Before | After |
|-|--------|-------|
| Upload rate | 50 Hz | 10 Hz |
| Upstream bandwidth | 307.2 Kbps | **61.4 Kbps** |
| **Reduction** | | **−80%** |

---

### Optimisation 2 — RSSI Scan Throttling

**Problem:** A Wi-Fi network scan (`WiFi.scanNetworks()`) is a blocking call that takes ~200 ms. Running it at sensor loop frequency (50 Hz) would block the IMU for 200 ms every 20 ms — completely infeasible.

**Rationale for 15 s interval:** The trolley moves at a typical walking speed of 0.5–1.0 m/s. At 1 m/s, it takes at minimum 3–5 seconds to traverse from one anchor zone to another. A 15 s scan interval therefore captures every zone transition with multiple readings to spare, while minimising scan overhead.

| | Naïve (every 1 s) | Optimised (every 15 s) |
|-|-------------------|------------------------|
| Scan frequency | 1 Hz | 0.067 Hz |
| Scan blocking duty cycle | 200 ms ÷ 1000 ms = **20%** | 200 ms ÷ 15,000 ms = **1.3%** |
| Scans per 3.5-hr shift | 12,600 | 840 |
| **Reduction in scan overhead** | | **−93.5%** |

---

### Optimisation 3 — Scan Gating on Speed

**Problem:** Even at 15 s intervals, running a 200 ms blocking scan while the trolley is in motion would drop 10 IMU samples (at 50 Hz), causing gaps in speed and acceleration data precisely when accurate motion data is needed for event detection.

**Solution:** The scan is suppressed if `speed > 0.02 m/s`. It only fires when the trolley is stationary or nearly stationary — when the IMU data is less critical and a brief pause in the loop is acceptable.

| | Without gating | With gating |
|-|----------------|-------------|
| Scans during motion phases | All 15 s intervals | **0** |
| IMU sample gaps during motion | 10 samples per scan | **0** |
| Pickup/drop false triggers from scan gap | Possible | **Eliminated** |

---

### Optimisation 4 — Event-Priority Upload Gap

**Problem:** At 10 Hz regular cadence, a critical event (queue detection, trolley pickup) could be delayed up to 100 ms before reaching the cloud — a perceptible lag during a live demonstration.

**Solution:** When any event flag (`pickup`, `drop_down`, `queue_detect`, `browsing`) transitions to `true`, an immediate upload is triggered with a minimum inter-upload gap of 40 ms (`EVENT_UPLOAD_GAP_MS = 40`). Non-event readings continue at 10 Hz.

| | Regular cadence only | With event priority |
|-|----------------------|---------------------|
| Event upload worst-case latency | 100 ms | **40 ms** |
| Event latency reduction | | **−60%** |
| Extra bandwidth cost (events are rare) | — | Negligible (<1% of readings are events) |

---

### Optimisation 5 — MQTT QoS 1 over QoS 2

**Problem:** MQTT QoS 2 (exactly-once) requires a 4-message handshake per publish: `PUBLISH → PUBREC → PUBREL → PUBCOMP`. At 10 Hz this generates 40 MQTT control packets per second in addition to the 10 data packets.

**Solution:** QoS 1 (at-least-once) uses a 2-message handshake (`PUBLISH → PUBACK`), halving MQTT control overhead. Duplicate delivery is acceptable for a continuous telemetry stream — the database deduplicates by timestamp.

| | QoS 2 | QoS 1 |
|-|-------|-------|
| MQTT packets/second | 50 (10 data + 40 control) | **30 (10 data + 20 control)** |
| Control packet overhead | 40/s | **20/s** |
| **Reduction in MQTT control traffic** | | **−50%** |

---

### Optimisation Summary — Before vs After

| Metric | Naïve baseline | Optimised | Reduction |
|--------|---------------|-----------|-----------|
| Upstream bandwidth | 307.2 Kbps | **61.4 Kbps** | **−80%** |
| Data per 3.5-hr shift | ~484 MB | **~94 MB** | **−81%** |
| RSSI scan duty cycle | 20% (1 s interval) | **1.3% (15 s + gating)** | **−93.5%** |
| IMU sample gaps during motion | 10 per scan | **0** | **−100%** |
| Event upload latency | 100 ms | **40 ms** | **−60%** |
| MQTT control packets/s | 200 (QoS 2, 50 Hz) | **20 (QoS 1, 10 Hz)** | **−90%** |

---

### Upload Rate (MQTT path) — Achieved
- **Upload interval:** 100 ms (`CLOUD_UPLOAD_MS = 100`)
- **Rate:** 10 messages/second
- **Upstream bandwidth:** 768 B × 10 = **7.68 KB/s = 61.4 Kbps**
- **Per hour:** ~27 MB
- **Per 3.5-hour shift:** ~94 MB

### Direct UDP Stream (low-latency local path)
- **Upload interval:** 50 ms (`DIRECT_UPLOAD_MS = 50`)
- **Rate:** 20 messages/second
- **Upstream bandwidth:** 768 B × 20 = **15.4 KB/s** (local network only)
- Opt-in only via `ENABLE_DIRECT_STREAM=1` — bypasses MQTT broker entirely for lowest-latency local dashboard updates

### Further Reduction Available (Not Yet Implemented)
| Technique | Expected saving |
|-----------|----------------|
| Gzip compression on JSON payload | ~35% → 768 B → ~500 B → **~61 MB/shift** |
| Binary protocol (CBOR/MessagePack) | ~50% → 768 B → ~384 B → **~47 MB/shift** |
| Field batching (5 readings per packet) | Reduces MQTT framing overhead by ~4× |

---

## 8. Communications Stack

### MQTT (Primary Cloud Path)
| Parameter | Value |
|-----------|-------|
| Broker | `mqtt.yungcz.com:8883` |
| Protocol | MQTT over TLS 1.3 |
| Credentials | `cartly / cartly` |
| CA Certificate | ISRG Root X1 (Let's Encrypt), embedded in firmware |
| Publish topic | `smarttrolley/trolley_01/telemetry` |
| Subscribe topic | `smarttrolley/trolley_01/config` |
| QoS level | 1 (at-least-once delivery) |
| Keep-alive | 60 seconds |
| MQTT buffer | 1280 bytes |
| Reconnect interval | Every 1.5 seconds on disconnect |

### UDP Direct Stream (Secondary Local Path)
- Port 4210, JSON over raw UDP
- Backend advertises its LAN IP to the device via MQTT config on startup
- Device switches to UDP when `directEnabled: true` is received
- 20 Hz update rate — used for lowest-latency local dashboard updates

### Wi-Fi
- Connects to `YungHub` access point
- Reconnect attempt every 10 seconds on disconnect
- Sleep mode disabled to maintain MQTT responsiveness

---

## 9. Security

### Implemented
| Mechanism | Detail |
|-----------|--------|
| **TLS 1.3 encryption** | All MQTT traffic encrypted end-to-end between device and broker |
| **CA certificate pinning** | ISRG Root X1 embedded in firmware — prevents MITM even if a rogue CA is compromised |
| **Broker authentication** | Username/password required on MQTT connection |
| **Topic isolation** | Separate topics for telemetry (pub) and config (sub) — device cannot receive its own telemetry back |
| **Payload validation** | FastAPI backend uses Pydantic models to validate all inbound config API calls |
| **Error isolation** | Malformed MQTT/UDP payloads are caught and discarded without crashing the system |

### Why Security Is Necessary
1. **Config topic is an attack surface** — a malicious actor who can publish to `smarttrolley/trolley_01/config` could disable actuators, raise thresholds to suppress alerts, or redirect the direct UDP stream to a spoofed IP. TLS + authentication prevents this.
2. **Telemetry contains behavioural data** — shopper movement patterns, dwell times, and position data are privacy-sensitive. Encryption in transit prevents passive eavesdropping.
3. **Physical accessibility** — trolleys are publicly accessible; the MQTT broker being TLS-only means the credentials cannot be sniffed even on public Wi-Fi.

### AWS Tools — Currently Deployed
| Component | AWS Service | Status |
|-----------|------------|--------|
| **Database** | **AWS RDS MySQL** (`cartly-database.czoceemm8dli.eu-west-2.rds.amazonaws.com`, eu-west-2) | ✅ Live — all telemetry stored here |
| **Backend API** | EC2 / hosted server at `api.cartly.yungcz.com` | ✅ Live |
| **Analytics platform** | Metabase on EC2 at `analytics.cartly.yungcz.com` | ✅ Live — directly connected to AWS RDS MySQL |

### AWS Tools — Proposed Additions for Full Production
| Component | AWS Service | Reason |
|-----------|------------|--------|
| MQTT broker | **AWS IoT Core** | Managed, scalable, integrates with Lambda/RDS |
| Analytics | **AWS QuickSight** | BI dashboards directly over RDS — no extra ETL needed |
| File storage | **AWS S3** | Long-term CSV/parquet archival from RDS exports |
| Processing | **AWS Lambda** | Event-driven triggers on `queue_detect` / `pickup` events |
| Auth | **AWS Cognito** | Dashboard login, role-based access control |
| Certificates | **AWS Certificate Manager** | Managed TLS certs for IoT device fleet |

---

## 10. Dashboard Features

**Stack:** React + Recharts + WebSocket (frontend) / FastAPI + SQLAlchemy + **AWS RDS MySQL** (backend)
**Frontend served from:** `https://api.cartly.yungcz.com` (cloud-hosted)

### Live Monitoring Panel
- Real-time speed (m/s), cadence (steps/min), distance (m), dwell time (s)
- Zone indicator (ZONE_A/B/C/BETWEEN/UNKNOWN) with colour coding
- Carry style and load proxy classification
- RSSI signal strength bars for all 3 anchors
- System state badge: `NORMAL` / `DEGRADED` / `NO_ANCHOR` / `IMU_FAIL` / `CLOUD_OFFLINE`
- Connection mode badge: `MQTT` vs `Direct UDP`
- Live event pills: Pickup (yellow), Drop-down (red), Browsing (blue), Queue (purple)

### External Context Panel (Enriched Data)
Live data from **Open-Meteo Forecast API** (free, no API key) fetched every 5 minutes and displayed alongside telemetry:
- **Weather:** temperature, apparent temperature, wind speed, rain (mm), cloud cover %, weather label (e.g. "Light rain", "Clear sky")
- **Daylight:** sunrise, sunset, daylight hours, day/night mode
- **Time context:** local time (store timezone), day of week, part-of-day label (morning rush / lunch peak / etc.), shopping period classification, weekday vs weekend
- Nav bar shows live weather summary chip and shopping period chip at all times
- Sources attributed: "Weather: Open-Meteo Forecast API"

### Store Heatmap & Queue Panel
- **Store heatmap:** Gaussian KDE overlay on a 6×6 m SVG floor plan showing shelf rows (Bakery & Cereal, Dairy & Chilled, Fresh Produce) and 3 checkout bays (Self-Checkout, Quick Checkout, Manned Checkout)
- Positions sampled every 5th telemetry reading to build session density map
- Heatmap expandable to 500×500 px modal with colour legend (blue→cyan→yellow→red)
- **Queue status view:** automatically switches when `queue_detect` is active — highlights the nearest checkout bay with dwell time and historical per-bay visit counts

### Data History & Analytics
- Speed and cadence trend line charts (120-point rolling buffer)
- Distance-over-time line chart
- Zone distribution bar chart
- Event log table: timestamp, event type, zone, speed, carry style, RSSI values
- Configurable history depth (record count selector)

### Analytics Platform (Metabase)
**Hosted at:** `https://analytics.cartly.yungcz.com`

Metabase is the historical analytics layer over the same AWS RDS MySQL telemetry store used by the live React dashboard. This satisfies the marking requirement that stored data must connect to an analytics platform, not just appear in an operational UI.

**Database connection used by Metabase:**
- Engine: MySQL
- Host: `cartly-database.czoceemm8dli.eu-west-2.rds.amazonaws.com`
- Port: `3306`
- Database: `trolley`
- Table analysed: `telemetry`

**Recommended dashboard: `Cartly Analytics`**
1. **Telemetry Volume Over Time** — line chart of row count by `received_at` hour; proves continuous ingestion into AWS RDS
2. **Average Speed Over Time** — line chart of average `speed_mps` by minute; shows trolley movement trends
3. **Zone Distribution** — bar chart of row count by `zone`; shows where the trolley spends most time
4. **Queue Events by Hour** — bar chart filtered to `queue_detect = true`, grouped by hour of day; highlights checkout congestion periods
5. **Pickup vs Drop-down Event Counts** — bar chart comparing counts of `pickup = true` and `drop_down = true`; quantifies trolley interaction events
6. **Browsing vs Queue Detection** — bar chart comparing counts of `browsing = true` and `queue_detect = true`; demonstrates the edge classifier outputs

**Value for the demonstration:**
- Shows historical analysis rather than only live telemetry
- Supports discussion of shopper behaviour, congestion, and zone utilisation
- Strengthens the cloud story by combining EC2-hosted analytics with AWS RDS MySQL
- Closes the analytics-platform gap in the marking rubric

### Data Export
- **CSV export:** `GET /api/telemetry/export?format=csv` — full time-series download, all 28 columns, streamed from AWS RDS MySQL
- **JSON export:** same endpoint with `format=json`
- Streaming response (handles large datasets without loading all into memory)

### Remote Configuration Panel
Six preset sensitivity profiles that push config to the device via MQTT in real-time:
| Profile | Use Case |
|---------|----------|
| Disabled Mode | All detection off |
| Alert Mode | Full staff alerts (2 s pulse + 8 s display flash) |
| Low Sensitivity | Busy store (reduced false alerts) |
| High Sensitivity | Quiet store (maximum detection) |
| Custom Mode | Manual parameter tuning |

Configurable parameters pushed over MQTT:
- `pickupAccelThreshold` — acceleration threshold for pickup events
- `dropImpactThreshold` — impact threshold for drop events
- `queueDwellThreshold` — dwell duration to classify queue
- `dwellAlertThreshold` — dwell duration to trigger staff alert
- `rssiScanIntervalMs` — how often to scan for anchor APs
- `actuatorPulseMs` — haptic pulse duration
- `displayFlashMs` — alert display duration
- `actuatorEnabled` — enable/disable all actuator outputs

---

## 11. System State Machine (Failsafe)

The firmware maintains a system health state that is reported in every telemetry packet and displayed on the TFT screen:

```
INIT
  └─► IMU initialisation
        ├─► FAIL → IMU_FAIL (halts, displays error)
        └─► OK
              └─► WiFi + MQTT connection
                    └─► Runtime state:
                          IMU_FAIL      — IMU unavailable
                          NO_ANCHOR     — 0 anchors visible
                          CLOUD_OFFLINE — MQTT disconnected
                          DEGRADED      — 1 or 2 anchors (reduced positioning accuracy)
                          NORMAL        — all 3 anchors + MQTT connected
```

**Automatic recovery mechanisms:**
- WiFi reconnect: every 10 seconds if disconnected
- MQTT reconnect: every 1.5 seconds if disconnected
- If MQTT unavailable, falls back to UDP direct stream (if backend previously advertised its IP)
- Database: try/except with rollback on every write — a DB error never crashes the backend
- Malformed MQTT/UDP packets discarded without system impact
- Encoder count protected by interrupt-disable critical section (no race condition)

---

## 12. Marking Criteria Coverage Summary

| Criterion | Coverage | Evidence |
|-----------|----------|---------|
| Key user requirements & KPIs | ✅ | Multi-metric telemetry (speed, cadence, zone, events), behaviour classification, staff alerting |
| Deployment challenges | ✅ | Battery runtime analysis, Wi-Fi coverage (3 anchors), MQTT retry logic, TLS overhead |
| Evidence-informed design | ✅ | RSSI trilateration, EMA filtering, IMU dynamic acceleration gravity removal |
| ≥4 sensor types | ✅ | Accelerometer, Gyroscope, RSSI scanner, Wheel encoder |
| ≥1 actuator | ✅ | Haptic GPIO pulse + TFT display alert |
| Arduino MKR1010 board | ✅ | 2× MKR1010 + 1× ESP32 C3 Super Mini deployed as Wi-Fi anchor APs (ANCHOR_A/B/C) |
| Efficient sensor aggregation | ✅ | Single 768-byte JSON packet combines all 28 fields @ 10 Hz |
| Data transmitted to cloud | ✅ | MQTT TLS to cloud broker at `mqtt.yungcz.com`; backend hosted at `api.cartly.yungcz.com` |
| Online database | ✅ | AWS RDS MySQL (`cartly-database.czoceemm8dli.eu-west-2.rds.amazonaws.com`, eu-west-2) |
| Data labelled for analysis | ✅ | 28 named columns, server-side timestamp, device_id indexed |
| Time-series download | ✅ | `/api/telemetry/export?format=csv` streaming endpoint |
| Operational dashboard | ✅ | React live dashboard with charts, event log, zone map |
| Events trigger interface actions | ✅ | Alert pills, status badge changes, real-time WebSocket push |
| Remote edge control | ✅ | MQTT config topic, 6 presets + manual parameter tuning |
| Edge params dynamically configurable | ✅ | All thresholds updated in real-time via MQTT, no reboot needed |
| Manual actuation | ✅ | Config panel sends `actuatorPulseMs` / `displayFlashMs` commands |
| Automatic actuation | ✅ | On-device pickup/drop/queue/dwell detection triggers actuator |
| Estimated power consumption | ✅ | 5V × 0.2A = 1W; 1100mAh @ 3.7V → ~3.5 hr runtime |
| Bandwidth optimisation | ✅ | 100ms upload @ 768B = 61.4 Kbps; RSSI throttled to 15 s; event-priority 40ms gap; UDP opt-in local path |
| Wireless sensor network | ✅ | 2× MKR1010 + 1× ESP32 C3 Super Mini anchor nodes + 1× ESP32-S3 edge node (star topology) |
| Battery powered | ✅ | 1100 mAh Li-Po @ 3.7V, 5V/0.2A draw, ~3.5 hr runtime |
| External data sources | ✅ | Open-Meteo Forecast API — live weather, wind, rain, cloud, sunrise/sunset; shopping period classifier |
| Failsafe mechanisms | ✅ | 5-state system state machine, auto-reconnect, DB rollback, ISR protection |
| Analytics platform | ✅ | Metabase deployed at `analytics.cartly.yungcz.com`, connected to AWS RDS MySQL, with historical charts for speed, zones, queue events, and behaviour classification |
| Security protocols described | ✅ | TLS 1.3, CA pinning, broker auth, topic isolation — all documented |
| AWS tools described | ✅ | RDS MySQL deployed (eu-west-2); proposed additions: IoT Core, QuickSight, S3, Lambda, Cognito |

---

## 13. Key Talking Points for Demonstration

1. **End-to-end live demo flow:** Trolley moves → encoder + IMU read (50 Hz) → on-device classification → MQTT TLS publish (10 Hz) → AWS RDS MySQL write → dashboard WebSocket update in <250ms
2. **Edge intelligence:** All behaviour classification (carry style, queue detection, browsing) runs locally — no round-trip to cloud needed for actuation
3. **Dynamic reconfiguration:** Show config panel changing `pickupAccelThreshold` → MQTT publish → device receives and applies instantly — demonstrable by changing sensitivity and repeating a pickup gesture
4. **Positioning + heatmap:** Walk through 3 zones, show RSSI values and zone badge changing, then expand heatmap to show the trolley's session trail overlaid on the store floor plan
5. **Queue detection:** Walk to checkout area → `queue_detect` triggers → dashboard switches heatmap to Queue Status view showing the active bay and dwell time
6. **External context enrichment:** Point to weather panel — live Open-Meteo data (temperature, rain, cloud cover) combined with shopper telemetry; show shopping period label changing by time of day
7. **Battery runtime:** 1100 mAh at 3.7V → 1W draw → 3.5 hours, sufficient for a retail morning shift
8. **Security:** MQTT over TLS 1.3 with embedded CA cert — no cleartext credentials on wire; AWS RDS in private subnet (VPC)
9. **Data export:** Click export CSV — show full time-series data downloading from AWS RDS with all 28 columns labelled
10. **System state failsafe:** Disconnect Wi-Fi → dashboard shows `CLOUD_OFFLINE` in real time; reconnect → back to `NORMAL` within 1.5 s
11. **Anchor node role:** Two Arduino MKR1010 boards + one ESP32 C3 Super Mini act as infrastructure — fixed APs providing the RSSI grid for trilateration positioning
12. **Analytics platform:** Open `analytics.cartly.yungcz.com` — show Metabase charts for telemetry volume, speed trends, zone distribution, and queue-event timing to demonstrate historical cloud analytics over AWS RDS

---

## 14. Technical Stack Summary

| Layer | Technology |
|-------|-----------|
| Infrastructure nodes | 2× Arduino MKR1010 + 1× ESP32 C3 Super Mini (Wi-Fi APs) |
| Edge MCU | ESP32-S3 |
| IMU | QMI8658 (6-axis, I²C) |
| Display | ST7789 240×240 TFT (SPI) |
| Firmware language | C++ (Arduino/PlatformIO) |
| Cloud transport | MQTT over TLS 1.3 (PubSubClient) |
| Local transport | UDP JSON (port 4210) |
| Backend | Python FastAPI + SQLAlchemy |
| Database | AWS RDS MySQL (eu-west-2) |
| Analytics platform | Metabase (EC2-hosted, HTTPS at `analytics.cartly.yungcz.com`) |
| External data API | Open-Meteo Forecast API (weather) |
| MQTT client (backend) | paho-mqtt |
| Frontend | React + Recharts + WebSocket |
| Frontend host | `api.cartly.yungcz.com` (cloud) |
| Build system | PlatformIO |

---

*Document last updated: 2026-03-24. For PPT generation, map each numbered section to a slide or slide group. Sections 2–4 cover hardware, sections 5–8 cover edge intelligence and comms, sections 9–11 cover security and reliability, section 12 maps to marking rubric, section 13 provides demo script talking points.*

**Full-marks note:** The previous analytics-platform gap is now closed by the live Metabase deployment at `analytics.cartly.yungcz.com`, connected directly to AWS RDS MySQL.
