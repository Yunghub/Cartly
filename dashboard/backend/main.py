import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from database import Base, SessionLocal, engine
import models as db_models
import schemas
from mqtt_client import publish_config, start_mqtt, stop_mqtt

Base.metadata.create_all(bind=engine)


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

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    start_mqtt(on_telemetry=_handle_telemetry, loop=loop)
    yield
    stop_mqtt()


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


@app.post("/api/config")
def send_config(payload: schemas.ConfigPayload):
    data = payload.model_dump(exclude_none=True)
    if not data:
        return {"status": "error", "message": "No fields provided"}
    publish_config(data)
    return {"status": "published", "payload": data}
