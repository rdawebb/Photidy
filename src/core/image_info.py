"""Module defining the ImageInfo dataclass for storing image metadata"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ImageInfo:
    path: Path
    timestamp: Optional[datetime]
    lat: Optional[float]
    lon: Optional[float]
    location: Optional[str]
