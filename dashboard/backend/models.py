from sqlalchemy import Column, Integer, Float, Boolean, String, DateTime
from sqlalchemy.sql import func
from database import Base


class TelemetryReading(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    received_at = Column(DateTime, server_default=func.now())

    # Device
    device_id = Column(String(64), index=True)
    timestamp_ms = Column(Integer)

    # Motion
    speed_mps = Column(Float)
    signed_speed_mps = Column(Float)
    distance_m = Column(Float)
    step_cadence_spm = Column(Float)

    # Events
    pickup = Column(Boolean)
    drop_down = Column(Boolean)
    dwell_time_ms = Column(Integer)

    # Classification
    carry_style = Column(String(32))
    load_proxy = Column(String(32))
    browsing = Column(Boolean)
    queue_detect = Column(Boolean)

    # Location / RSSI
    anchor_a_rssi = Column(Integer)
    anchor_b_rssi = Column(Integer)
    anchor_c_rssi = Column(Integer)
    anchors_seen = Column(Integer)
    zone = Column(String(64))
    pos_x_m = Column(Float)
    pos_y_m = Column(Float)
    live_hotspot = Column(String(64))

    # System
    imu_ok = Column(Boolean)
    aws_ok = Column(Boolean)
    system_state = Column(String(32))
