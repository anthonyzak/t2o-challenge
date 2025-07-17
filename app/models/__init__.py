"""
Models package initialization.
"""

import pkgutil
from pathlib import Path

from app.models.base import BaseModel
from app.models.weather import City, WeatherData, WeatherImportLog

__all__ = ["BaseModel", "City", "WeatherData", "WeatherImportLog"]


def load_all_models() -> None:
    """Load all models from this folder."""
    package_dir = Path(__file__).resolve().parent
    modules = pkgutil.walk_packages(
        path=[str(package_dir)],
        prefix="app.models.",
    )
    for module in modules:
        __import__(module.name)
