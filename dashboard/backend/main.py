import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import csv, io

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

_UDP_PORT = 4210


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
    udp_transport, _ = await loop.create_datagram_endpoint(
        lambda: _UDPListener(loop),
        local_addr=("0.0.0.0", _UDP_PORT),
    )
    print(f"[UDP] Listening for direct stream on port {_UDP_PORT}")
    start_mqtt(on_telemetry=_handle_telemetry, loop=loop)
    yield
    stop_mqtt()
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
