"""
Cartly Edge Demonstration — PowerPoint Generator  (v2)
Dark dashboard theme · logo on every slide · all text ≥ 12 pt
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = RGBColor(0x0a,0x0a,0x0a)
CARD    = RGBColor(0x14,0x14,0x14)
CARD2   = RGBColor(0x1c,0x1c,0x1c)
BORDER  = RGBColor(0x2a,0x2a,0x2a)
WHITE   = RGBColor(0xFF,0xFF,0xFF)
OFF     = RGBColor(0xE5,0xE7,0xEB)
MUTED   = RGBColor(0x71,0x71,0x7A)
MUTED2  = RGBColor(0x52,0x52,0x5B)
GREEN   = RGBColor(0x22,0xC5,0x5E)
AMBER   = RGBColor(0xF5,0x9E,0x0B)
BLUE    = RGBColor(0x37,0x99,0xF6)
BLUE2   = RGBColor(0x25,0x63,0xEB)
VIOLET  = RGBColor(0xA8,0x55,0xF7)
RED     = RGBColor(0xEF,0x44,0x44)

W = Inches(13.33)
H = Inches(7.5)
LOGO = r"y:\Documents\UCL\Year3\ELEC0033\cartly_logo_crop.png"
# logo is 1528×228 px  →  aspect 6.7:1.  We show at 1.8" wide → 0.27" tall
LOGO_W = Inches(1.8)
LOGO_H = Inches(0.27)

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H
blank = prs.slide_layouts[6]

# ── Primitive helpers ─────────────────────────────────────────────────────────
def slide():
    s = prs.slides.add_slide(blank)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    return s

def box(s, x, y, w, h, fill=CARD, border=BORDER, bw=Pt(0.75)):
    sh = s.shapes.add_shape(1, x, y, w, h)
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = border; sh.line.width = bw
    return sh

def txt(s, text, x, y, w, h, size=Pt(13), bold=False, color=WHITE,
        align=PP_ALIGN.LEFT, italic=False):
    tf = s.shapes.add_textbox(x, y, w, h)
    tf.word_wrap = True
    p = tf.text_frame.paragraphs[0]
    p.alignment = align
    r = p.add_run(); r.text = text
    r.font.size = size; r.font.bold = bold
    r.font.color.rgb = color; r.font.italic = italic
    r.font.name = "Calibri"
    return tf

def rule(s, x, y, w, color=BORDER):
    ln = s.shapes.add_connector(1, x, y, x+w, y)
    ln.line.color.rgb = color; ln.line.width = Pt(0.5)

def logo(s, right_margin=Inches(0.35), top=Inches(0.22)):
    """Place the Cartly logo top-right on every slide."""
    x = W - LOGO_W - right_margin
    s.shapes.add_picture(LOGO, x, top, LOGO_W, LOGO_H)

def eyebrow(s, text, x, y, w, color=MUTED):
    txt(s, text.upper(), x, y, w, Inches(0.28), size=Pt(9), bold=True, color=color)

def heading(s, text, x, y, w, size=Pt(24), color=WHITE):
    txt(s, text, x, y, w, Inches(0.45), size=size, bold=True, color=color)

def chip(s, text, x, y, fill, tc=WHITE, w=None, h=Inches(0.3)):
    cw = w or Inches(max(1.1, len(text)*0.105 + 0.3))
    box(s, x, y, cw, h, fill=fill, border=fill)
    txt(s, text, x, y+Inches(0.02), cw, h, size=Pt(10), bold=True, color=tc, align=PP_ALIGN.CENTER)
    return cw

def bullets(s, items, x, y, w, size=Pt(12), color=OFF, gap=Inches(0.32)):
    cy = y
    for item in items:
        txt(s, "·  " + item, x, cy, w, Inches(0.3), size=size, color=color)
        cy += gap
    return cy

def kpi(s, label, value, unit, x, y, w=Inches(2.2), accent=GREEN):
    h = Inches(1.15)
    box(s, x, y, w, h)
    txt(s, label, x+Inches(0.14), y+Inches(0.09), w-Inches(0.28), Inches(0.24),
        size=Pt(9), color=MUTED, bold=True)
    txt(s, value, x+Inches(0.14), y+Inches(0.33), w-Inches(0.28), Inches(0.46),
        size=Pt(26), bold=True, color=accent)
    txt(s, unit, x+Inches(0.14), y+Inches(0.84), w-Inches(0.28), Inches(0.24),
        size=Pt(9.5), color=MUTED2)

def table(s, headers, rows, x, y, w, cws, hcolor=BLUE, rh=Inches(0.34)):
    """Simple table: one header row + data rows."""
    # header
    box(s, x, y, w, rh, fill=RGBColor(0x14,0x22,0x3a), border=BORDER)
    cx = x
    for h_txt, cw in zip(headers, cws):
        txt(s, h_txt, cx+Inches(0.09), y+Inches(0.06), cw-Inches(0.12), rh,
            size=Pt(10), bold=True, color=hcolor)
        cx += cw
    # rows
    for ri, row in enumerate(rows):
        ry = y + rh*(ri+1)
        box(s, x, ry, w, rh, fill=CARD if ri%2==0 else CARD2, border=BORDER)
        cx = x
        for ci, (cell, cw) in enumerate(zip(row, cws)):
            c = OFF if ci == 0 else MUTED
            if str(cell).startswith("✅"): c = GREEN
            elif str(cell).startswith("⚠"): c = AMBER
            txt(s, str(cell), cx+Inches(0.09), ry+Inches(0.06), cw-Inches(0.12), rh,
                size=Pt(10), color=c)
            cx += cw

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — TITLE
# ═══════════════════════════════════════════════════════════════════════════════
s = slide()
# glow blobs
for cx,cy,r,col in [(Inches(1.0),Inches(1.3),Inches(2.2),RGBColor(0x03,0x10,0x2e)),
                    (Inches(12.3),Inches(6.3),Inches(2.0),RGBColor(0x02,0x14,0x0c))]:
    sh = s.shapes.add_shape(9, cx-r, cy-r, r*2, r*2)
    sh.fill.solid(); sh.fill.fore_color.rgb = col; sh.line.fill.background()

# Big logo centred on title slide — larger than the corner logo
s.shapes.add_picture(LOGO, Inches(3.5), Inches(1.4), Inches(6.33), Inches(0.945))

txt(s, "Smart Trolley Intelligence Platform",
    Inches(1.5), Inches(2.75), Inches(10.33), Inches(0.5),
    size=Pt(22), color=MUTED, align=PP_ALIGN.CENTER)

rule(s, Inches(3.8), Inches(3.42), Inches(5.73), color=BORDER)

chips_data = [("ESP32-S3 Edge",BLUE2),("AWS RDS MySQL",GREEN),
              ("MQTT TLS 1.3",VIOLET),("Open-Meteo",AMBER),("Metabase Analytics",BLUE2)]
total_w = sum(Inches(max(1.4,len(t)*0.115+0.4))+Inches(0.14) for t,_ in chips_data)
cx = (W - total_w)/2
for label, col in chips_data:
    cw = Inches(max(1.4, len(label)*0.115+0.4))
    chip(s, label, cx, Inches(3.75), col, w=cw)
    cx += cw + Inches(0.14)

txt(s, "ELEC0033  ·  UCL Year 3  ·  Edge Demonstration",
    Inches(1.5), Inches(6.85), Inches(10.33), Inches(0.4),
    size=Pt(11), color=MUTED2, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — SYSTEM ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "System Architecture", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "Three-Tier Edge Deployment", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

layers = [
    ("01","INFRASTRUCTURE","2× MKR1010 + 1× ESP32 C3", AMBER, [
        "2× MKR1010 + 1× ESP32 C3 Super Mini as static Wi-Fi APs",
        "SSIDs: ANCHOR_A  ·  ANCHOR_B  ·  ANCHOR_C",
        "Fixed positions in store",
        "Trolley passively scans RSSI every 15 s",
        "Forms indoor positioning grid",
    ]),
    ("02","EDGE LAYER","ESP32-S3 on Trolley", GREEN, [
        "50 Hz sensor loop (20 ms)",
        "8 on-device classifiers — no cloud inference",
        "Haptic actuator + TFT display alerts",
        "MQTT TLS 1.3 publish at 10 Hz",
        "Continues locally if cloud offline",
    ]),
    ("03","CLOUD / DASHBOARD","AWS + FastAPI + React", BLUE, [
        "MQTT broker: mqtt.yungcz.com:8883",
        "AWS RDS MySQL (eu-west-2)",
        "FastAPI + WebSocket: api.cartly.yungcz.com",
        "Metabase: analytics.cartly.yungcz.com",
        "Open-Meteo weather enrichment",
    ]),
]
cw = Inches(3.95); gap = Inches(0.24); sx = Inches(0.5)
for i,(num,title,sub,acc,buls) in enumerate(layers):
    cx = sx + i*(cw+gap)
    box(s, cx, Inches(1.15), cw, Inches(6.0), fill=CARD, border=acc)
    txt(s, num, cx+Inches(0.2), Inches(1.28), Inches(0.6), Inches(0.45),
        size=Pt(30), bold=True, color=acc)
    txt(s, title, cx+Inches(0.2), Inches(1.75), cw-Inches(0.35), Inches(0.3),
        size=Pt(11), bold=True, color=acc)
    txt(s, sub,   cx+Inches(0.2), Inches(2.08), cw-Inches(0.35), Inches(0.3),
        size=Pt(13), bold=True, color=WHITE)
    rule(s, cx+Inches(0.2), Inches(2.44), cw-Inches(0.4), color=acc)
    bullets(s, buls, cx+Inches(0.2), Inches(2.6), cw-Inches(0.35),
            size=Pt(12), color=OFF, gap=Inches(0.55))

for i in range(2):
    ax = sx + (i+1)*(cw+gap) - gap + Inches(0.04)
    txt(s, "→", ax, Inches(3.9), gap, Inches(0.4), size=Pt(20), color=MUTED, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — USER REQUIREMENTS & KPIs
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Requirements", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "User Requirements & Performance Indicators", Inches(0.5), Inches(0.52), Inches(10))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

req_rows = [
    ("Store staff",   "Real-time alerts when trolley enters checkout queue"),
    ("Store staff",   "Immediate notification on pickup or drop"),
    ("Store manager", "Historical analytics: zone utilisation, events, movement"),
    ("Operator",      "Adjust detection sensitivity remotely — no physical access needed"),
    ("Operator",      "Live health status of every deployed trolley at a glance"),
    ("System",        "Battery-powered and untethered — fits trolley form factor"),
    ("System",        "Data persisted centrally for cross-session analysis"),
    ("System",        "Edge processing continues if cloud connectivity is lost"),
]
table(s, ["User / Role", "Requirement"], req_rows,
      Inches(0.5), Inches(1.15), Inches(6.5),
      [Inches(1.5), Inches(5.0)], rh=Inches(0.365))

kpis = [
    ("Telemetry Rate",  "10 Hz",   "100 ms MQTT",      BLUE),
    ("Event Latency",   "40 ms",   "Priority upload",  GREEN),
    ("IMU Sample Rate", "50 Hz",   "20 ms loop",       BLUE),
    ("Battery Runtime", "3.5 hr",  "1100 mAh @ 1W",   AMBER),
    ("MQTT Reconnect",  "<1.5 s",  "Firmware retry",   GREEN),
    ("DB Columns",      "28",      "All labelled",     VIOLET),
]
kx = Inches(7.2); ky = Inches(1.15)
for i,(lbl,val,unit,acc) in enumerate(kpis):
    r, c = i//2, i%2
    kpi(s, lbl, val, unit, kx+c*Inches(3.0), ky+r*Inches(1.26), w=Inches(2.85), accent=acc)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — FOUR SENSORS
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Hardware · Sensing", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "Four Sensor Types", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

sensors = [
    ("01","IMU Accelerometer","QMI8658 · 3-axis · 50 Hz", GREEN, [
        "Linear accel X/Y/Z (mg)",
        "Dynamic accel — gravity removed",
        "Pickup threshold: 2.5 m/s²",
        "Drop threshold: 4.0 m/s²",
        "Step cadence from peak detection",
        "Vibration RMS via EMA",
    ]),
    ("02","IMU Gyroscope","QMI8658 · 3-axis · 50 Hz", BLUE, [
        "Angular velocity X/Y/Z (dps)",
        "Turn rate EMA for queue detection",
        "Carry style orientation tracking",
        "Yaw for dead-reckoning position",
        "Same chip — distinct modality",
    ]),
    ("03","RSSI Scanner","Wi-Fi 2.4 GHz · every 15 s", VIOLET, [
        "RSSI from ANCHOR_A/B/C (dBm)",
        "Log-distance path loss model",
        "Zone: A / B / C / BETWEEN",
        "2D trilateration (posX, posY)",
        "Gaussian KDE heatmap",
    ]),
    ("04","Wheel Encoder","Magnetic · GPIO ISR · 50 Hz", AMBER, [
        "3 counts per revolution",
        "Wheel ⌀ 45.2 mm (caliper-verified)",
        "Resolution ≈ 47 mm per count",
        "Signed speed (direction-aware)",
        "EMA-smoothed · ISR protected",
    ]),
]
cw = Inches(3.0); gap = Inches(0.22); sx = Inches(0.5)
for i,(num,name,sub,acc,buls) in enumerate(sensors):
    cx = sx + i*(cw+gap)
    box(s, cx, Inches(1.15), cw, Inches(6.0), fill=CARD, border=acc)
    chip(s, sub, cx+Inches(0.12), Inches(1.27), acc, w=cw-Inches(0.24), h=Inches(0.28))
    txt(s, num, cx+Inches(0.15), Inches(1.65), Inches(0.55), Inches(0.42),
        size=Pt(24), bold=True, color=acc)
    txt(s, name, cx+Inches(0.15), Inches(2.1), cw-Inches(0.3), Inches(0.32),
        size=Pt(14), bold=True, color=WHITE)
    rule(s, cx+Inches(0.15), Inches(2.48), cw-Inches(0.3), color=acc)
    bullets(s, buls, cx+Inches(0.15), Inches(2.64), cw-Inches(0.28),
            size=Pt(11.5), color=OFF, gap=Inches(0.45))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — EDGE INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Edge Intelligence", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "On-Device Behaviour Classification", Inches(0.5), Inches(0.52), Inches(10))
txt(s, "All 8 classifiers run locally on the ESP32-S3 — no cloud round-trip required for actuation",
    Inches(0.5), Inches(0.96), Inches(10), Inches(0.28), size=Pt(12), color=MUTED)
rule(s, Inches(0.5), Inches(1.28), Inches(12.33))

classifiers = [
    ("Carry Style",       "5-state rule-based",              "Speed · pitch/roll · vibration · aDyn",    "LIFTED / PARKED / TILTED_PUSH / ROUGH_ROLL / SMOOTH_ROLL", GREEN),
    ("Pickup Detection",  "aDyn threshold > 2.5 m/s²",      "Accelerometer",                            "→ 200 ms haptic + cloud event flag",                        AMBER),
    ("Drop Detection",    "aDyn threshold > 4.0 m/s²",      "Accelerometer",                            "→ 200 ms haptic + cloud event flag",                        RED),
    ("Dwell Detection",   "Speed < 0.02 m/s timed state",   "Encoder speed",                            "→ Staff alert after 4 s pause",                             BLUE),
    ("Browsing",          "Slow + turn rate + dwell combo",  "Encoder + gyro + dwell timer",             "→ Blue event pill on dashboard",                            BLUE),
    ("Queue Detection",   "Creep + low turn + stop-go",      "All sensors fused",                        "→ 300 ms haptic + checkout bay highlight",                  VIOLET),
    ("Step Cadence",      "Peak detection on |aDyn|",        "Accelerometer",                            "→ Steps per minute in telemetry",                           GREEN),
    ("Load Proxy",        "EMA: vibration + jerk + speed",   "Accel + encoder",                          "→ Estimated load level in telemetry",                       AMBER),
]
cw = Inches(6.12); ch = Inches(0.88); gx = Inches(0.21); gy = Inches(0.1)
ox = Inches(0.5); oy = Inches(1.42)
for i,(name,algo,inputs,output,acc) in enumerate(classifiers):
    cx = ox + (i%2)*(cw+gx)
    cy = oy + (i//2)*(ch+gy)
    box(s, cx, cy, cw, ch, fill=CARD, border=acc)
    txt(s, name,   cx+Inches(0.15), cy+Inches(0.08), cw-Inches(0.3), Inches(0.28), size=Pt(13), bold=True, color=WHITE)
    txt(s, f"Algorithm: {algo}",  cx+Inches(0.15), cy+Inches(0.37), cw-Inches(0.3), Inches(0.22), size=Pt(10.5), color=MUTED)
    txt(s, f"Inputs: {inputs}", cx+Inches(0.15), cy+Inches(0.57), cw-Inches(0.3), Inches(0.22), size=Pt(10.5), color=MUTED)
    txt(s, output, cx+Inches(0.15), cy+Inches(0.7), cw-Inches(0.3), Inches(0.16), size=Pt(10), color=acc)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — ACTUATORS & FAILSAFE
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Actuation & Reliability", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "Actuators & System Health State Machine", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

# Actuator 1 — TFT Display
box(s, Inches(0.5), Inches(1.15), Inches(5.9), Inches(5.2), fill=CARD, border=RED)
txt(s, "ACTUATOR 1", Inches(0.72), Inches(1.27), Inches(5.5), Inches(0.26),
    size=Pt(10), bold=True, color=RED)
txt(s, "ST7789 TFT Display — 240×240", Inches(0.72), Inches(1.55), Inches(5.5), Inches(0.32),
    size=Pt(15), bold=True, color=WHITE)
bullets(s, [
    "Red/white alternating flash at 180 ms intervals",
    '"ATTENTION — Check trolley — Staff alerted"',
    "Duration configurable via MQTT: displayFlashMs",
    "Normal mode: status display (speed, zone, system state)",
    "Shows live speed (m/s), zone label, and system state",
    'Remotely disableable via MQTT:  { "actuatorEnabled": false }',
], Inches(0.72), Inches(1.98), Inches(5.5), size=Pt(11.5), gap=Inches(0.38))

# State machine right
box(s, Inches(6.6), Inches(1.15), Inches(6.25), Inches(5.2), fill=CARD, border=BORDER)
txt(s, "5-STATE HEALTH MONITOR", Inches(6.82), Inches(1.27), Inches(5.9), Inches(0.26),
    size=Pt(10), bold=True, color=MUTED)
txt(s, "System State Machine", Inches(6.82), Inches(1.55), Inches(5.9), Inches(0.32),
    size=Pt(15), bold=True, color=WHITE)
rule(s, Inches(6.82), Inches(1.94), Inches(5.8), color=BORDER)
states = [
    ("NORMAL",         "All 3 anchors + MQTT connected",             GREEN),
    ("DEGRADED",       "1–2 anchors — reduced positioning accuracy", AMBER),
    ("CLOUD_OFFLINE",  "MQTT disconnected — edge still operates",    AMBER),
    ("NO_ANCHOR",      "0 anchors — zone classification disabled",   RED),
    ("IMU_FAIL",       "IMU init failed — halts with error screen",  RED),
]
sy = Inches(2.08)
for state,desc,acc in states:
    box(s, Inches(6.82), sy, Inches(5.8), Inches(0.54), fill=CARD2, border=acc)
    chip(s, state, Inches(6.92), sy+Inches(0.1), acc, w=Inches(1.8), h=Inches(0.32))
    txt(s, desc, Inches(8.82), sy+Inches(0.14), Inches(3.65), Inches(0.28),
        size=Pt(11), color=OFF)
    sy += Inches(0.62)
txt(s, "Auto-recovery: WiFi retry every 10 s · MQTT retry every 1.5 s · DB rollback on write error",
    Inches(6.82), Inches(5.28), Inches(5.8), Inches(0.28), size=Pt(10.5), color=MUTED)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — POWER BUDGET
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Resource Evaluation", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "Power Budget", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

# Battery card
box(s, Inches(0.5), Inches(1.15), Inches(4.1), Inches(5.9), fill=CARD, border=GREEN)
txt(s, "BATTERY SPEC", Inches(0.7), Inches(1.28), Inches(3.7), Inches(0.26),
    size=Pt(10), bold=True, color=GREEN)
txt(s, "1100 mAh Li-Po", Inches(0.7), Inches(1.57), Inches(3.7), Inches(0.44),
    size=Pt(24), bold=True, color=WHITE)
rule(s, Inches(0.7), Inches(2.06), Inches(3.5), color=GREEN)
specs = [
    ("Cell voltage",    "3.7 V"),
    ("Capacity",        "1,100 mAh"),
    ("Energy stored",   "4.07 Wh"),
    ("Supply voltage",  "5 V via boost"),
    ("Current draw",    "0.20 A"),
    ("Active power",    "1.00 W"),
    ("Converter eff.",  "~87%"),
    ("Usable energy",   "3.54 Wh"),
    ("Runtime",         "~3.5 hours"),
]
ry = Inches(2.22)
for k,v in specs:
    txt(s, k, Inches(0.7), ry, Inches(2.1), Inches(0.3), size=Pt(11), color=MUTED)
    txt(s, v, Inches(2.82), ry, Inches(1.3), Inches(0.3), size=Pt(11), bold=True, color=WHITE, align=PP_ALIGN.RIGHT)
    ry += Inches(0.35)

# Power consumers
box(s, Inches(4.78), Inches(1.15), Inches(4.2), Inches(3.0), fill=CARD, border=BORDER)
txt(s, "CURRENT BREAKDOWN", Inches(4.98), Inches(1.28), Inches(3.8), Inches(0.26),
    size=Pt(10), bold=True, color=MUTED)
txt(s, "Power Consumers", Inches(4.98), Inches(1.57), Inches(3.8), Inches(0.32),
    size=Pt(14), bold=True, color=WHITE)
consumers = [
    ("Wi-Fi radio (always-on)", "~150 mA", AMBER),
    ("ST7789 TFT + backlight",  "~30 mA",  BLUE),
    ("ESP32-S3 core",           "~20 mA",  GREEN),
    ("QMI8658 IMU",             "~1 mA",   MUTED),
]
cy2 = Inches(2.0)
for name,ma,acc in consumers:
    txt(s, name, Inches(4.98), cy2, Inches(2.8), Inches(0.3), size=Pt(12), color=OFF)
    txt(s, ma, Inches(7.8), cy2, Inches(1.0), Inches(0.3), size=Pt(12), bold=True, color=acc, align=PP_ALIGN.RIGHT)
    cy2 += Inches(0.38)

# Optimisation note
box(s, Inches(4.78), Inches(4.32), Inches(4.2), Inches(2.73), fill=CARD, border=AMBER)
txt(s, "OPTIMISATION NOTE", Inches(4.98), Inches(4.45), Inches(3.8), Inches(0.26),
    size=Pt(10), bold=True, color=AMBER)
bullets(s, [
    "Wi-Fi sleep disabled for MQTT responsiveness",
    "Enabling DTIM modem sleep → −30–40% power",
    "Would extend runtime to ~5 hours",
    "Trade-off: +100 ms reconnect latency",
], Inches(4.98), Inches(4.77), Inches(3.8), size=Pt(12), gap=Inches(0.38))

# Runtime card
box(s, Inches(9.15), Inches(1.15), Inches(3.7), Inches(5.9), fill=CARD, border=GREEN)
txt(s, "RUNTIME", Inches(9.35), Inches(1.28), Inches(3.3), Inches(0.26),
    size=Pt(10), bold=True, color=GREEN)
txt(s, "~3.5 hrs", Inches(9.35), Inches(1.58), Inches(3.3), Inches(0.7),
    size=Pt(48), bold=True, color=GREEN)
txt(s, "per charge cycle", Inches(9.35), Inches(2.32), Inches(3.3), Inches(0.3),
    size=Pt(12), color=MUTED)
rule(s, Inches(9.35), Inches(2.7), Inches(3.1), color=GREEN)
calcs = [
    "4.07 Wh × 0.87 = 3.54 Wh usable",
    "3.54 Wh ÷ 1.0 W = 3.54 hours",
    "",
    "Sufficient for a full retail",
    "morning session.",
    "",
    "Charge between AM / PM shifts.",
]
ry2 = Inches(2.86)
for line in calcs:
    txt(s, line, Inches(9.35), ry2, Inches(3.3), Inches(0.32),
        size=Pt(12), color=OFF if line else MUTED)
    ry2 += Inches(0.4)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — BANDWIDTH PROOF
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Resource Evaluation · Bandwidth", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "Proof of Optimised Bandwidth", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

# 4 headline tiles
for i,(lbl,val,sub,acc) in enumerate([
    ("NAÏVE BASELINE", "307.2 Kbps", "50 Hz · no rate limiter", RED),
    ("OPTIMISED",      "61.4 Kbps",  "10 Hz · decoupled upload", GREEN),
    ("REDUCTION",      "−80%",        "Less upstream traffic",    GREEN),
    ("DATA / SHIFT",   "94 MB",       "vs 484 MB naïve (−81%)",   BLUE),
]):
    kpi(s, lbl, val, sub, Inches(0.5)+i*Inches(3.21), Inches(1.12), w=Inches(3.05), accent=acc)

# Optimisation breakdown
opt = [
    ("Upload rate decoupling",  "Sensor 50 Hz stays intact   →   Upload rate capped at 10 Hz",          "307 → 61.4 Kbps",    "−80%",    GREEN),
    ("RSSI scan throttling",    "Every loop tick (infeasible) →   Every 15 s (configurable)",           "20% → 1.3% duty",    "−93.5%",  GREEN),
    ("Speed-gated scanning",    "Scans during motion         →   Only when speed < 0.02 m/s",           "IMU gaps: 10 → 0",   "−100%",   GREEN),
    ("Event-priority upload",   "Embedded in 100 ms cadence →    Immediate at 40 ms gap",               "Latency: 100→40 ms", "−60%",    AMBER),
    ("MQTT QoS 1 vs QoS 2",    "4-packet handshake          →   2-packet handshake",                    "200 → 20 ctrl/s",    "−90%",    BLUE),
]
table(s, ["Optimisation", "What Changed", "Impact", "Δ"],
      [r[:4] for r in opt],
      Inches(0.5), Inches(2.4), Inches(12.33),
      [Inches(2.5), Inches(5.08), Inches(2.5), Inches(1.0)+Inches(0.25)],
      rh=Inches(0.44))

box(s, Inches(0.5), Inches(6.55), Inches(12.33), Inches(0.72), fill=CARD2, border=BORDER)
txt(s, "768 B JSON payload · 28 fields per reading  ·  "
       "Future savings: gzip −35% → ~61 MB/shift  ·  CBOR binary −50% → ~47 MB/shift  ·  "
       "UDP direct path (port 4210) bypasses MQTT on local LAN",
    Inches(0.65), Inches(6.68), Inches(12.0), Inches(0.45),
    size=Pt(11), color=MUTED)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — COMMUNICATIONS & SECURITY
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Communications & Security", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "MQTT Stack & Security Architecture", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

# MQTT params left
box(s, Inches(0.5), Inches(1.15), Inches(5.8), Inches(4.15), fill=CARD, border=BLUE)
txt(s, "MQTT · PRIMARY CLOUD PATH", Inches(0.7), Inches(1.28), Inches(5.4), Inches(0.26),
    size=Pt(10), bold=True, color=BLUE)
params = [
    ("Broker",      "mqtt.yungcz.com : 8883"),
    ("Protocol",    "MQTT over TLS 1.3  (RFC 8446)"),
    ("CA cert",     "ISRG Root X1 — pinned in firmware"),
    ("Auth",        "Username + password"),
    ("Publish",     "smarttrolley/trolley_01/telemetry"),
    ("Subscribe",   "smarttrolley/trolley_01/config"),
    ("QoS",         "1 — at-least-once"),
    ("Reconnect",   "Every 1.5 s on disconnect"),
]
py = Inches(1.58)
for k,v in params:
    txt(s, k,  Inches(0.7),  py, Inches(1.5),  Inches(0.32), size=Pt(11), color=MUTED)
    txt(s, v,  Inches(2.24), py, Inches(3.9),  Inches(0.32), size=Pt(11), color=OFF)
    py += Inches(0.36)

# Why security box
box(s, Inches(0.5), Inches(5.45), Inches(5.8), Inches(1.8), fill=CARD, border=GREEN)
txt(s, "WHY SECURITY IS NECESSARY", Inches(0.7), Inches(5.58), Inches(5.4), Inches(0.26),
    size=Pt(10), bold=True, color=GREEN)
bullets(s, [
    "Config topic is an attack surface — rogue client could disable actuators",
    "Telemetry contains privacy-sensitive movement & dwell data",
    "Publicly accessible device on Wi-Fi — TLS prevents sniffing",
], Inches(0.7), Inches(5.9), Inches(5.5), size=Pt(11), gap=Inches(0.36))

# Security mechanisms right
mechs = [
    ("TLS 1.3 Encryption",       "IETF RFC 8446 · all MQTT traffic encrypted · 1-RTT handshake", GREEN),
    ("CA Certificate Pinning",   "ISRG Root X1 hardcoded in firmware — prevents MITM attacks",   GREEN),
    ("Broker Authentication",    "Username + password on every connect · topic-level isolation",  GREEN),
    ("Payload Validation",       "FastAPI + Pydantic validates all inbound config API calls",     BLUE),
    ("Error Isolation",          "Malformed MQTT / UDP payloads caught & discarded gracefully",   BLUE),
    ("AWS RDS Security",         "Database in private subnet (VPC) — not publicly reachable",    VIOLET),
]
mx = Inches(6.5); my = Inches(1.15)
for title,desc,acc in mechs:
    box(s, mx, my, Inches(6.35), Inches(0.94), fill=CARD, border=acc)
    txt(s, title, mx+Inches(0.15), my+Inches(0.1),  Inches(6.0), Inches(0.3), size=Pt(13), bold=True, color=WHITE)
    txt(s, desc,  mx+Inches(0.15), my+Inches(0.44), Inches(6.0), Inches(0.4), size=Pt(11), color=MUTED)
    my += Inches(1.02)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — DASHBOARD & ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Dashboard & Analytics", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "Dashboard Features & Metabase Analytics", Inches(0.5), Inches(0.52), Inches(10))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

panels = [
    ("Live Monitoring", BLUE, [
        "Speed · cadence · distance · dwell time",
        "Zone: A / B / C / BETWEEN / UNKNOWN",
        "RSSI bars for all 3 anchors",
        "State badge: NORMAL / DEGRADED / OFFLINE",
        "Event pills: Pickup · Drop · Browsing · Queue",
        "WebSocket push — updates in < 250 ms",
    ]),
    ("Store Heatmap & Queue", VIOLET, [
        "Gaussian KDE over 6×6 m SVG floor plan",
        "Shelf rows + 3 checkout bays mapped",
        "Switches to Queue Status on queue_detect",
        "Highlights active checkout bay + dwell time",
        "Expandable to 500×500 px full modal",
        "Session density from RSSI trilateration",
    ]),
    ("External Context", AMBER, [
        "Open-Meteo API — refreshed every 5 min",
        "Temperature · feels-like · wind · rain",
        "Sunrise / sunset / daylight hours",
        "Part-of-day & shopping period labels",
        "Weekday vs weekend classification",
        "Weather chip always visible in nav bar",
    ]),
    ("Metabase Analytics", GREEN, [
        "analytics.cartly.yungcz.com (EC2)",
        "Connected directly to AWS RDS MySQL",
        "Telemetry volume over time",
        "Average speed · zone distribution",
        "Queue events by hour of day",
        "Pickup vs drop event counts",
    ]),
]
cw = Inches(3.0); gap = Inches(0.22); sx = Inches(0.5)
for i,(title,acc,buls) in enumerate(panels):
    cx = sx + i*(cw+gap)
    box(s, cx, Inches(1.15), cw, Inches(5.95), fill=CARD, border=acc)
    txt(s, title, cx+Inches(0.15), Inches(1.28), cw-Inches(0.3), Inches(0.32),
        size=Pt(14), bold=True, color=WHITE)
    rule(s, cx+Inches(0.15), Inches(1.65), cw-Inches(0.3), color=acc)
    bullets(s, buls, cx+Inches(0.15), Inches(1.82), cw-Inches(0.28),
            size=Pt(11.5), color=OFF, gap=Inches(0.44))

box(s, Inches(0.5), Inches(7.1), Inches(12.33), Inches(0.28), fill=CARD2, border=BORDER)
txt(s, "Export: GET /api/telemetry/export?format=csv  ·  GET .../export?format=json  ·  "
       "All 28 columns · streamed from AWS RDS MySQL",
    Inches(0.65), Inches(7.14), Inches(12.0), Inches(0.22), size=Pt(10), color=MUTED)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — EVIDENCE-INFORMED DESIGN
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Design Rationale", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "Evidence-Informed Design Choices", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

choices = [
    ("RSSI Trilateration",    "Log-distance path loss — Rappaport (2002)",
     "RSSI(d) = RSSI(d₀) − 10n·log₁₀(d/d₀)  ·  n = 2.2 (open retail)  ·  d₀ = 1 m @ −56 dBm measured empirically", BLUE),
    ("EMA Filtering",         "O(1) noise rejection vs SMA",
     "α = 0.1–0.3 tuned empirically  ·  Applied to: speed, vibration RMS, jerk, turn rate, cadence", GREEN),
    ("Gravity Removal",       "Dynamic accel isolation — Bao & Intille (2004)",
     "aDyn = raw accel − EMA(gravity)  ·  Prevents false pickup/drop triggers on a tilted trolley", GREEN),
    ("MQTT Protocol",         "ISO/IEC 20922 — purpose-built for constrained IoT",
     "QoS 1 guarantees delivery without QoS 2 double-handshake overhead  ·  Pub/sub = natural access control", BLUE),
    ("TLS 1.3",               "IETF RFC 8446 · OWASP IoT cert pinning guidance",
     "1-RTT vs TLS 1.2 2-RTT  ·  Critical for 1.5 s MQTT reconnect cycle  ·  ISRG Root X1 pinned in firmware", VIOLET),
    ("Empirical Calibration", "All thresholds set via repeated physical tests",
     "Pickup 2.5 m/s² · Drop 4.0 m/s² · Queue dwell 3 s · Encoder CPR manually verified · Wheel ⌀ caliper-measured", AMBER),
]
cw = Inches(6.12); ch = Inches(0.98); gx = Inches(0.21); gy = Inches(0.1)
ox = Inches(0.5); oy = Inches(1.15)
for i,(title,source,detail,acc) in enumerate(choices):
    cx = ox + (i%2)*(cw+gx)
    cy = oy + (i//2)*(ch+gy)
    box(s, cx, cy, cw, ch, fill=CARD, border=acc)
    txt(s, title,  cx+Inches(0.15), cy+Inches(0.09), cw-Inches(0.3), Inches(0.3), size=Pt(13), bold=True, color=WHITE)
    txt(s, source, cx+Inches(0.15), cy+Inches(0.42), cw-Inches(0.3), Inches(0.22), size=Pt(11), bold=True, color=acc)
    txt(s, detail, cx+Inches(0.15), cy+Inches(0.66), cw-Inches(0.3), Inches(0.28), size=Pt(10), color=MUTED)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 12 — AWS & CLOUD STACK
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Cloud Architecture", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "AWS Stack — Deployed & Proposed", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

txt(s, "CURRENTLY LIVE", Inches(0.5), Inches(1.15), Inches(6.0), Inches(0.26),
    size=Pt(10), bold=True, color=GREEN)
deployed = [
    ("AWS RDS MySQL",         "eu-west-2",   "cartly-database.czoceemm8dli.eu-west-2.rds.amazonaws.com : 3306"),
    ("EC2 Backend API",       "eu-west-2",   "api.cartly.yungcz.com  (FastAPI + paho-mqtt + SQLAlchemy)"),
    ("Metabase Analytics",    "EC2-hosted",  "analytics.cartly.yungcz.com — connected to RDS MySQL"),
]
dy = Inches(1.45)
for svc,region,url in deployed:
    box(s, Inches(0.5), dy, Inches(6.1), Inches(0.96), fill=CARD, border=GREEN)
    chip(s, "✓  LIVE", Inches(0.65), dy+Inches(0.14), GREEN, w=Inches(1.1), h=Inches(0.28))
    txt(s, svc, Inches(1.85), dy+Inches(0.12), Inches(4.6), Inches(0.28), size=Pt(13), bold=True, color=WHITE)
    txt(s, f"{region}  ·  {url}", Inches(1.85), dy+Inches(0.44), Inches(4.6), Inches(0.42), size=Pt(10), color=MUTED)
    dy += Inches(1.04)

txt(s, "PROPOSED ADDITIONS", Inches(0.5), Inches(4.6), Inches(6.0), Inches(0.26),
    size=Pt(10), bold=True, color=AMBER)
proposed = [
    ("AWS IoT Core",            "Managed MQTT — scalable, Lambda-integrated"),
    ("AWS QuickSight",          "BI dashboards over RDS — no extra ETL"),
    ("AWS S3",                  "Long-term CSV/parquet archival from RDS"),
    ("AWS Lambda",              "Event triggers on queue_detect / pickup"),
    ("AWS Cognito",             "Dashboard auth — staff vs manager roles"),
]
py2 = Inches(4.9)
for svc,reason in proposed:
    box(s, Inches(0.5), py2, Inches(6.1), Inches(0.4), fill=CARD2, border=BORDER)
    txt(s, svc,    Inches(0.65), py2+Inches(0.07), Inches(2.0), Inches(0.26), size=Pt(11), bold=True, color=AMBER)
    txt(s, reason, Inches(2.7),  py2+Inches(0.07), Inches(3.75), Inches(0.26), size=Pt(11), color=MUTED)
    py2 += Inches(0.44)

# Data flow right
box(s, Inches(6.8), Inches(1.15), Inches(6.05), Inches(6.12), fill=CARD, border=BORDER)
txt(s, "END-TO-END DATA FLOW", Inches(7.0), Inches(1.28), Inches(5.7), Inches(0.26),
    size=Pt(10), bold=True, color=MUTED)
txt(s, "How data moves through the system",
    Inches(7.0), Inches(1.57), Inches(5.7), Inches(0.3), size=Pt(13), bold=True, color=WHITE)
rule(s, Inches(7.0), Inches(1.94), Inches(5.6), color=BORDER)
flow = [
    ("ESP32-S3 Sensors",   "50 Hz IMU · encoder · RSSI",          GREEN),
    ("MQTT TLS 1.3",       "mqtt.yungcz.com:8883 · QoS 1 · 10 Hz",BLUE),
    ("FastAPI Backend",    "api.cartly.yungcz.com · WebSocket",    BLUE),
    ("AWS RDS MySQL",      "eu-west-2 · 28 cols · timestamped",    GREEN),
    ("React Dashboard",    "Live WebSocket · < 250 ms latency",    BLUE),
    ("Metabase Analytics", "analytics.cartly.yungcz.com · SQL BI", VIOLET),
    ("Open-Meteo API",     "Weather enrichment · 5 min cache",     AMBER),
]
fy = Inches(2.08)
for i,(node,desc,acc) in enumerate(flow):
    box(s, Inches(7.0), fy, Inches(5.6), Inches(0.52), fill=CARD2, border=acc)
    txt(s, node, Inches(7.15), fy+Inches(0.07), Inches(2.3), Inches(0.26), size=Pt(11.5), bold=True, color=WHITE)
    txt(s, desc, Inches(7.15), fy+Inches(0.29), Inches(5.2), Inches(0.2),  size=Pt(10),   color=MUTED)
    fy += Inches(0.6)
    if i < len(flow)-1:
        txt(s, "↓", Inches(9.8), fy-Inches(0.14), Inches(0.4), Inches(0.22),
            size=Pt(12), color=MUTED2, align=PP_ALIGN.CENTER)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 13 — MARKING CRITERIA (split 2 columns to keep text readable)
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Assessment", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "Marking Criteria — All Covered", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

criteria = [
    ("Specifications",  "Key user requirements & KPIs",          "Rappaport·Bao·RFC8446·OWASP refs"),
    ("Specifications",  "Deployment challenges considered",       "Battery life·anchors·MQTT retry·TLS"),
    ("Specifications",  "Evidence-informed design choices",       "Literature + empirical calibration"),
    ("End-to-End",      "≥4 sensor types",                       "Accel · Gyro · RSSI · Encoder"),
    ("End-to-End",      "≥1 actuator + MKR1010 board",           "TFT display · 2×MKR1010 + 1×C3 as APs"),
    ("End-to-End",      "Data transmitted to cloud",             "MQTT TLS → mqtt.yungcz.com → RDS"),
    ("Data",            "Online database",                       "AWS RDS MySQL eu-west-2"),
    ("Data",            "Labelled for analysis",                 "28 named columns + timestamp"),
    ("Data",            "Time-series download",                  "/api/telemetry/export?format=csv"),
    ("UI",              "Operational dashboard",                 "React · live WS · heatmap · config"),
    ("UI",              "Sensors trigger interface actions",     "Alert pills · state badge · WS push"),
    ("UI",              "Remote control of edge system",        "6 presets + custom → MQTT config"),
    ("Edge Control",    "Dynamically configurable, any location","MQTT config sub · OTA · no reboot"),
    ("Edge Control",    "Manual & automatic actuation",          "Config panel + on-device classifiers"),
    ("Resources",       "Estimated power consumption",           "5V×0.2A=1W · 3.54Wh÷1W=3.5hr"),
    ("Resources",       "Proof of optimised bandwidth",          "307→61 Kbps (−80%) · 5 optimisations"),
    ("Optimised",       "Wireless sensor network",               "2×MKR1010 + 1×C3 + ESP32-S3 star topology"),
    ("Optimised",       "Battery powered",                       "1100mAh Li-Po · 3.5hr runtime"),
    ("Enriched",        "External data sources",                 "Open-Meteo API · weather · daylight"),
    ("Enriched",        "Failsafe mechanisms",                   "5-state machine · reconnect · rollback"),
    ("Enriched",        "Analytics platform",                    "Metabase @ analytics.cartly.yungcz.com"),
    ("Security",        "Security protocols + why",              "TLS 1.3 · CA pin · auth · isolation"),
    ("Security",        "AWS tools described",                   "RDS live · IoT Core/QS/S3 proposed"),
]

# Split into 2 columns of 12 and 11
half = 12
col_data = [criteria[:half], criteria[half:]]
for col_i, col_rows in enumerate(col_data):
    cx = Inches(0.5) + col_i * Inches(6.42)
    cw_total = Inches(6.22)
    col_ws = [Inches(1.42), Inches(2.62), Inches(2.18)]
    headers = ["Category", "Criterion", "Evidence"]
    table(s, headers, [("✅ "+r[0], r[1], r[2]) for r in col_rows],
          cx, Inches(1.15), cw_total, col_ws, rh=Inches(0.31))

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 14 — DEMO SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Live Demonstration", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "Demo Script — Talking Points", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

steps = [
    ("01","End-to-End Flow",
     "Move trolley → 50 Hz sensors → 8 classifiers → MQTT TLS 10 Hz → AWS RDS → dashboard WebSocket < 250 ms", GREEN),
    ("02","Edge Intelligence",
     "Trigger pickup — haptic fires immediately with no cloud round-trip. Show on-device actuation is instant.", GREEN),
    ("03","Dynamic Reconfiguration",
     "Config panel: change pickupAccelThreshold → MQTT publish → device applies instantly → repeat pickup gesture.", BLUE),
    ("04","Positioning & Heatmap",
     "Walk zones A→B→C: RSSI + zone badge change. Expand heatmap to show session trail on 6×6 m floor plan.", VIOLET),
    ("05","Queue Detection",
     "Enter checkout area → queue_detect fires → dashboard switches to Queue Status view → bay highlighted + dwell.", AMBER),
    ("06","External Context",
     "Show weather panel: Open-Meteo live temperature/rain/cloud + shopping period label in nav bar chips.", AMBER),
    ("07","Power & Battery",
     "1100 mAh @ 3.7V → 1W draw → 3.5 hr runtime at 5V × 0.2A. Sufficient for retail morning shift.", GREEN),
    ("08","Security Demo",
     "MQTT runs over TLS 1.3. ISRG Root X1 CA pinned in firmware. AWS RDS in private VPC subnet.", GREEN),
    ("09","Data Export",
     "Click Download CSV → full time-series streamed from AWS RDS · 28 labelled columns · all readings.", BLUE),
    ("10","Failsafe Demo",
     "Disconnect Wi-Fi → CLOUD_OFFLINE badge. Reconnect → NORMAL within 1.5 s. Edge keeps running throughout.", RED),
    ("11","Metabase Analytics",
     "Open analytics.cartly.yungcz.com → show speed trends, zone distribution, queue events by hour from AWS RDS.", VIOLET),
    ("12","Anchor Node Role",
     "2× Arduino MKR1010 + 1× ESP32 C3 Super Mini = infrastructure APs. Each broadcasts a fixed SSID. Trolley scans RSSI every 15 s.", AMBER),
]
cw2 = Inches(6.12); ch2 = Inches(0.82); gx2 = Inches(0.21); gy2 = Inches(0.1)
ox2 = Inches(0.5); oy2 = Inches(1.15)
for i,(num,title,detail,acc) in enumerate(steps):
    cx = ox2 + (i%2)*(cw2+gx2)
    cy = oy2 + (i//2)*(ch2+gy2)
    box(s, cx, cy, cw2, ch2, fill=CARD, border=acc)
    txt(s, num,   cx+Inches(0.14), cy+Inches(0.1),  Inches(0.42), Inches(0.26), size=Pt(11), bold=True, color=acc)
    txt(s, title, cx+Inches(0.58), cy+Inches(0.08), cw2-Inches(0.72), Inches(0.28), size=Pt(12), bold=True, color=WHITE)
    txt(s, detail,cx+Inches(0.14), cy+Inches(0.44), cw2-Inches(0.28), Inches(0.36), size=Pt(10.5), color=MUTED)

# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 15 — TECH STACK
# ═══════════════════════════════════════════════════════════════════════════════
s = slide(); logo(s)
eyebrow(s, "Technical Stack", Inches(0.5), Inches(0.22), Inches(8))
heading(s, "Full Technical Stack", Inches(0.5), Inches(0.52), Inches(9))
rule(s, Inches(0.5), Inches(1.02), Inches(12.33))

stack = [
    ("Infrastructure",  "2× MKR1010 + 1× ESP32 C3",   "Wi-Fi APs · ANCHOR_A/B/C",              AMBER),
    ("Edge MCU",        "ESP32-S3",                   "50 Hz loop · 8 classifiers · C++",       GREEN),
    ("IMU",             "QMI8658  (6-axis, I²C)",     "Accel + Gyro · GPIO 47/48",              GREEN),
    ("Display",         "ST7789 240×240 TFT (SPI)",   "Status + alert flash",                   BLUE),
    ("Firmware",        "C++ · Arduino · PlatformIO", "PubSubClient · Arduino_GFX",             MUTED),
    ("Cloud Transport", "MQTT over TLS 1.3",          "PubSubClient · ISRG Root X1 pinned",     BLUE),
    ("Local Transport", "UDP JSON · port 4210",       "Opt-in · 20 Hz · bypasses broker",       MUTED),
    ("Backend",         "Python FastAPI + SQLAlchemy","api.cartly.yungcz.com",                  BLUE),
    ("Database",        "AWS RDS MySQL (eu-west-2)",  "cartly-database.czoceemm8dli…",          GREEN),
    ("Analytics",       "Metabase on EC2",            "analytics.cartly.yungcz.com",            VIOLET),
    ("External Data",   "Open-Meteo Forecast API",    "Weather · free · no API key needed",     AMBER),
    ("MQTT Client",     "paho-mqtt",                  "Backend subscriber · TLS verified",       MUTED),
    ("Frontend",        "React + Recharts + WS",      "api.cartly.yungcz.com (cloud-hosted)",   BLUE),
    ("Build",           "PlatformIO",                 "ESP32-S3 Arduino target",                MUTED),
]
sw = Inches(3.98); sgap = Inches(0.1); sx2 = Inches(0.5)
sy = Inches(1.15)
cols3 = 3
for i,(layer,tech,detail,acc) in enumerate(stack):
    col = i % cols3; row = i // cols3
    cx = sx2 + col*(sw+sgap)
    cy = sy  + row*Inches(0.82)
    box(s, cx, cy, sw, Inches(0.75), fill=CARD, border=acc)
    txt(s, layer,  cx+Inches(0.14), cy+Inches(0.07), Inches(1.3),        Inches(0.24), size=Pt(9),    bold=True, color=acc)
    txt(s, tech,   cx+Inches(0.14), cy+Inches(0.3),  sw-Inches(0.28),    Inches(0.26), size=Pt(12),   bold=True, color=WHITE)
    txt(s, detail, cx+Inches(0.14), cy+Inches(0.54), sw-Inches(0.28),    Inches(0.2),  size=Pt(10),   color=MUTED)

box(s, Inches(0.5), Inches(7.1), Inches(12.33), Inches(0.28), fill=CARD2, border=BORDER)
txt(s, "Cartly  ·  ELEC0033  ·  UCL Year 3  ·  Edge Demonstration  ·  All marking criteria ✅",
    Inches(0.65), Inches(7.14), Inches(12.0), Inches(0.22),
    size=Pt(11), color=MUTED, align=PP_ALIGN.CENTER)

# ── Save ──────────────────────────────────────────────────────────────────────
OUT = r"y:\Documents\UCL\Year3\ELEC0033\Cartly_Edge_Demo.pptx"
prs.save(OUT)
print(f"Saved: {OUT}  ({len(prs.slides)} slides)")
