import asyncio
import csv
import io
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from database import Base, SessionLocal, engine
import models as db_models
import schemas
from mqtt_client import publish_config, start_mqtt, stop_mqtt

Base.metadata.create_all(bind=engine)

_STORE_CONTEXT = {
    "name": "Cartly Demo Store",
    "latitude": 51.5246,
    "longitude": -0.1340,
    "timezone": "Europe/London",
}
_WEATHER_CACHE_TTL_S = 15 * 60
_external_cache: dict = {"expires_at": 0.0, "payload": None}

_WEATHER_CODE_LABELS = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Moderate showers",
    82: "Violent showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm with hail",
}


def _part_of_day(hour: int) -> str:
    if hour < 6:
        return "night"
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    if hour < 21:
        return "evening"
    return "night"


def _shopping_period(local_now: datetime) -> str:
    hour = local_now.hour
    if hour < 8:
        return "closed"
    if hour < 11:
        return "morning rush"
    if hour < 14:
        return "lunch peak"
    if hour < 17:
        return "afternoon browse"
    if hour < 20:
        return "after-work peak"
    if hour < 22:
        return "late evening"
    return "closed"


def _fetch_external_context() -> dict:
    local_now = datetime.now(ZoneInfo(_STORE_CONTEXT["timezone"]))
    params = urlencode(
        {
            "latitude": _STORE_CONTEXT["latitude"],
            "longitude": _STORE_CONTEXT["longitude"],
            "current": ",".join(
                [
                    "temperature_2m",
                    "apparent_temperature",
                    "precipitation",
                    "rain",
                    "cloud_cover",
                    "wind_speed_10m",
                    "weather_code",
                    "is_day",
                ]
            ),
            "daily": "sunrise,sunset,daylight_duration",
            "forecast_days": 1,
            "timezone": _STORE_CONTEXT["timezone"],
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    with urlopen(url, timeout=8) as response:
        raw = json.loads(response.read().decode("utf-8"))

    current = raw.get("current", {})
    daily = raw.get("daily", {})
    sunrise = (daily.get("sunrise") or [None])[0]
    sunset = (daily.get("sunset") or [None])[0]
    daylight_duration = (daily.get("daylight_duration") or [None])[0]

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "location": _STORE_CONTEXT,
        "time": {
            "local_iso": local_now.isoformat(),
            "weekday": local_now.strftime("%A"),
            "date_label": local_now.strftime("%d %b %Y"),
            "time_label": local_now.strftime("%H:%M:%S"),
            "is_weekend": local_now.weekday() >= 5,
            "part_of_day": _part_of_day(local_now.hour),
            "shopping_period": _shopping_period(local_now),
        },
        "weather": {
            "temperature_c": current.get("temperature_2m"),
            "apparent_temperature_c": current.get("apparent_temperature"),
            "wind_kph": current.get("wind_speed_10m"),
            "precipitation_mm": current.get("precipitation"),
            "rain_mm": current.get("rain"),
            "cloud_cover_pct": current.get("cloud_cover"),
            "weather_code": current.get("weather_code"),
            "weather_label": _WEATHER_CODE_LABELS.get(
                current.get("weather_code"), "Unknown"
            ),
            "is_day": bool(current.get("is_day", 0)),
        },
        "sun": {
            "sunrise": sunrise,
            "sunset": sunset,
            "daylight_hours": round(float(daylight_duration or 0) / 3600, 2),
        },
        "sources": {
            "time": "Backend server timezone context",
            "weather": "Open-Meteo Forecast API",
        },
    }


def _get_external_context() -> dict:
    now = datetime.utcnow().timestamp()
    cached = _external_cache.get("payload")
    if cached and now < _external_cache["expires_at"]:
        return cached

    try:
        payload = _fetch_external_context()
    except (TimeoutError, URLError, ValueError) as exc:
        if cached:
            stale = dict(cached)
            stale["stale"] = True
            stale["warning"] = f"External context refresh failed: {exc}"
            return stale
        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "location": _STORE_CONTEXT,
            "time": {
                "local_iso": datetime.now(
                    ZoneInfo(_STORE_CONTEXT["timezone"])
                ).isoformat(),
                "weekday": None,
                "date_label": None,
                "time_label": None,
                "is_weekend": None,
                "part_of_day": None,
                "shopping_period": None,
            },
            "weather": None,
            "sun": None,
            "sources": {
                "time": "Backend server timezone context",
                "weather": "Open-Meteo Forecast API",
            },
            "stale": True,
            "warning": f"External context unavailable: {exc}",
        }

    _external_cache["payload"] = payload
    _external_cache["expires_at"] = now + _WEATHER_CACHE_TTL_S
    return payload


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self._active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._active.remove(ws) if ws in self._active else None

    async def broadcast(self, data: dict) -> None:
        msg = json.dumps(data, default=str)
        dead = []
        for ws in list(self._active):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _save_reading(data: dict) -> None:
    db = SessionLocal()
    try:
        reading = db_models.TelemetryReading(
            device_id=data.get("device_id"),
            timestamp_ms=data.get("timestamp_ms"),
            speed_mps=data.get("speed_mps"),
            signed_speed_mps=data.get("signed_speed_mps"),
            distance_m=data.get("distance_m"),
            step_cadence_spm=data.get("step_cadence_spm"),
            pickup=data.get("pickup"),
            drop_down=data.get("drop_down"),
            dwell_time_ms=data.get("dwell_time_ms"),
            carry_style=data.get("carry_style"),
            load_proxy=data.get("load_proxy"),
            browsing=data.get("browsing"),
            queue_detect=data.get("queue_detect"),
            anchor_a_rssi=data.get("anchor_a_rssi"),
            anchor_b_rssi=data.get("anchor_b_rssi"),
            anchor_c_rssi=data.get("anchor_c_rssi"),
            anchors_seen=data.get("anchors_seen"),
            zone=data.get("zone"),
            pos_x_m=data.get("pos_x_m"),
            pos_y_m=data.get("pos_y_m"),
            live_hotspot=data.get("live_hotspot"),
            imu_ok=data.get("imu_ok"),
            aws_ok=data.get("aws_ok"),
            system_state=data.get("system_state"),
        )
        db.add(reading)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB] Save error: {e}")
    finally:
        db.close()


def _row_to_dict(row) -> dict:
    d = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    if d.get("received_at"):
        d["received_at"] = d["received_at"].isoformat()
    return d


# ---------------------------------------------------------------------------
# MQTT telemetry handler (called from MQTT thread via run_coroutine_threadsafe)
# ---------------------------------------------------------------------------

async def _handle_telemetry(data: dict) -> None:
    await asyncio.to_thread(_save_reading, data)
    await manager.broadcast(data)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

_UDP_PORT = 4210
_ENABLE_DIRECT_STREAM = os.getenv("ENABLE_DIRECT_STREAM", "0") == "1"


class _UDPListener(asyncio.DatagramProtocol):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def datagram_received(self, data: bytes, addr) -> None:
        try:
            payload = json.loads(data.decode())
            payload["_direct"] = True
            self._loop.create_task(_handle_telemetry(payload))
        except Exception as e:
            print(f"[UDP] Bad packet from {addr}: {e}")

    def error_received(self, exc) -> None:
        print(f"[UDP] Error: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    udp_transport = None
    if _ENABLE_DIRECT_STREAM:
        udp_transport, _ = await loop.create_datagram_endpoint(
            lambda: _UDPListener(loop),
            local_addr=("0.0.0.0", _UDP_PORT),
        )
        print(f"[UDP] Listening for direct stream on port {_UDP_PORT}")
    start_mqtt(on_telemetry=_handle_telemetry, loop=loop)
    yield
    stop_mqtt()
    if udp_transport:
        udp_transport.close()


app = FastAPI(title="Smart Trolley API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # Send the most recent reading immediately on connect
    db = SessionLocal()
    try:
        row = (
            db.query(db_models.TelemetryReading)
            .order_by(db_models.TelemetryReading.id.desc())
            .first()
        )
        if row:
            await ws.send_text(json.dumps(_row_to_dict(row), default=str))
    finally:
        db.close()

    try:
        while True:
            await ws.receive_text()  # keep alive; client can send pings
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/context/external")
def get_external_context():
    return _get_external_context()


@app.get("/api/devices")
def get_devices():
    db = SessionLocal()
    try:
        rows = db.query(db_models.TelemetryReading.device_id).distinct().all()
        return [r[0] for r in rows if r[0]]
    finally:
        db.close()


@app.get("/api/telemetry/latest")
def get_latest(device_id: Optional[str] = None):
    db = SessionLocal()
    try:
        q = db.query(db_models.TelemetryReading).order_by(
            db_models.TelemetryReading.id.desc()
        )
        if device_id:
            q = q.filter(db_models.TelemetryReading.device_id == device_id)
        row = q.first()
        return _row_to_dict(row) if row else {}
    finally:
        db.close()


@app.get("/api/telemetry/history")
def get_history(
    limit: int = 200,
    offset: int = 0,
    device_id: Optional[str] = None,
):
    db = SessionLocal()
    try:
        q = db.query(db_models.TelemetryReading).order_by(
            db_models.TelemetryReading.id.desc()
        )
        if device_id:
            q = q.filter(db_models.TelemetryReading.device_id == device_id)
        rows = q.offset(offset).limit(limit).all()
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


@app.get("/api/telemetry/export")
def export_telemetry(device_id: Optional[str] = None, format: str = "csv"):
    db = SessionLocal()
    try:
        q = db.query(db_models.TelemetryReading).order_by(
            db_models.TelemetryReading.id.asc()
        )
        if device_id:
            q = q.filter(db_models.TelemetryReading.device_id == device_id)
        rows = q.all()
        if format == "csv":
            buf = io.StringIO()
            if rows:
                cols = [c.name for c in db_models.TelemetryReading.__table__.columns]
                writer = csv.DictWriter(buf, fieldnames=cols)
                writer.writeheader()
                for row in rows:
                    writer.writerow(_row_to_dict(row))
            buf.seek(0)
            return StreamingResponse(
                iter([buf.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=telemetry.csv"},
            )
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


@app.get("/api/telemetry/stats")
def get_stats(device_id: Optional[str] = None):
    from sqlalchemy import func as sqlfunc
    db = SessionLocal()
    try:
        q = db.query(db_models.TelemetryReading)
        if device_id:
            q = q.filter(db_models.TelemetryReading.device_id == device_id)
        total = q.count()
        if total == 0:
            return {"total": 0, "avg_speed_mps": 0, "avg_cadence_spm": 0,
                    "max_distance_m": 0, "pickup_count": 0, "drop_count": 0, "queue_count": 0}
        avg_speed = db.query(sqlfunc.avg(db_models.TelemetryReading.speed_mps)).scalar() or 0
        avg_cadence = db.query(sqlfunc.avg(db_models.TelemetryReading.step_cadence_spm)).scalar() or 0
        max_distance = db.query(sqlfunc.max(db_models.TelemetryReading.distance_m)).scalar() or 0
        pickup_count = q.filter(db_models.TelemetryReading.pickup == True).count()
        drop_count = q.filter(db_models.TelemetryReading.drop_down == True).count()
        queue_count = q.filter(db_models.TelemetryReading.queue_detect == True).count()
        return {
            "total": total,
            "avg_speed_mps": round(float(avg_speed), 3),
            "avg_cadence_spm": round(float(avg_cadence), 1),
            "max_distance_m": round(float(max_distance), 2),
            "pickup_count": pickup_count,
            "drop_count": drop_count,
            "queue_count": queue_count,
        }
    finally:
        db.close()


@app.post("/api/config")
def send_config(payload: schemas.ConfigPayload):
    data = payload.model_dump(exclude_none=True)
    if not data:
        return {"status": "error", "message": "No fields provided"}
    publish_config(data)
    return {"status": "published", "payload": data}
