"""Safe public configuration schemas."""

from typing import Dict, List
from pydantic import BaseModel


class ConfigData(BaseModel):
    """Safe configuration exposed to frontend clients."""

    app_name: str
    version: str
    environment: str
    default_currency: str
    default_locale: str
    default_timezone: str
    supported_upload_formats: List[str]
    max_upload_size_bytes: int
    is_synthetic_only: bool = True
    features: Dict[str, bool]

