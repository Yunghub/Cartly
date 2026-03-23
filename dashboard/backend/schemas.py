from pydantic import BaseModel
from typing import Optional


class ConfigPayload(BaseModel):
    pickupAccelThreshold: Optional[float] = None
    dropImpactThreshold: Optional[float] = None
    queueDwellThreshold: Optional[int] = None
    dwellAlertThreshold: Optional[int] = None
    rssiScanIntervalMs: Optional[int] = None
    actuatorEnabled: Optional[bool] = None
    actuatorPulseMs: Optional[int] = None
    displayFlashMs: Optional[int] = None
    directHost: Optional[str] = None
    directPort: Optional[int] = None
    directEnabled: Optional[bool] = None
