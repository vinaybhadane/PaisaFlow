"""Health check schemas."""

from pydantic import BaseModel


class HealthData(BaseModel):
    """Health check payload."""

    status: str
    app_name: str
    version: str
    environment: str
    database: str

