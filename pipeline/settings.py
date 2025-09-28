"""Central configuration for the foreclosure processing pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

# Base paths
BASE_DIR: Final[Path] = Path(__file__).resolve().parent
ROOT_DIR: Final[Path] = BASE_DIR.parent

LOCAL_DIR: Final[Path] = BASE_DIR / "testing"

CASE_DOCS_DIR: Final[Path] = LOCAL_DIR / "case_docs"
OUTPUT_DIR: Final[Path] = LOCAL_DIR / "output"
MANUAL_JSON_PATH: Final[Path] = LOCAL_DIR / "manual.json"
ERROR_LOG_PATH: Final[Path] = LOCAL_DIR / "error_log.json"
CASE_SCRAPER_LOG_PATH: Final[Path] = LOCAL_DIR / "case_scraper.log"
FINAL_RESULTS_PATH: Final[Path] = LOCAL_DIR / "final_results.csv"

# Service account handling
DEFAULT_SERVICE_ACCOUNT_PATHS = (
    BASE_DIR / "service_account.json",
    LOCAL_DIR / "service_account.json",
    ROOT_DIR / "service_account.json",
)


def get_service_account_path() -> Path:
    """Return the first existing service account path."""
    for candidate in DEFAULT_SERVICE_ACCOUNT_PATHS:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Unable to find service_account.json. Place it in pipeline/ or project root."
    )


SERVICE_ACCOUNT_PATH: Final[Path] = get_service_account_path()

# External services
GCS_BUCKET: Final[str] = os.getenv("PIPELINE_GCS_BUCKET", "orange-county-records-search")
VERTEX_PROJECT: Final[str] = os.getenv("PIPELINE_VERTEX_PROJECT", "flipping-automation")
VERTEX_LOCATION: Final[str] = os.getenv("PIPELINE_VERTEX_LOCATION", "europe-west4")
VERTEX_MODEL: Final[str] = os.getenv("PIPELINE_VERTEX_MODEL", "gemini-1.5-pro-001")

NOPECHA_KEY: Final[str | None] = os.getenv("PIPELINE_NOPECHA_KEY")
RAPIDAPI_KEY: Final[str | None] = os.getenv("PIPELINE_RAPIDAPI_KEY")
FILEMAKER_BASIC_AUTH: Final[str | None] = os.getenv("PIPELINE_FILEMAKER_BASIC")
FILEMAKER_BEARER_TOKEN: Final[str | None] = os.getenv("PIPELINE_FILEMAKER_BEARER")
FILEMAKER_COUNTY_ID: Final[str] = os.getenv(
    "PIPELINE_FILEMAKER_COUNTY_ID", "C82CDF06-179F-45E0-AC9E-F8869D93616C"
)

GOOGLE_SEARCH_RAPIDAPI_HOST: Final[str] = "google-search74.p.rapidapi.com"
ZILLOW_RAPIDAPI_HOST: Final[str] = "zillow-com1.p.rapidapi.com"

# Chrome / Selenium
CHROME_EXTENSION_DIR: Final[Path] = LOCAL_DIR / "nopecha_extension"


def ensure_directories() -> None:
    """Ensure directories that the pipeline depends on exist."""
    for path in (CASE_DOCS_DIR, OUTPUT_DIR, CHROME_EXTENSION_DIR):
        path.mkdir(parents=True, exist_ok=True)


__all__ = [
    "BASE_DIR",
    "ROOT_DIR",
    "LOCAL_DIR",
    "CASE_DOCS_DIR",
    "OUTPUT_DIR",
    "MANUAL_JSON_PATH",
    "ERROR_LOG_PATH",
    "CASE_SCRAPER_LOG_PATH",
    "FINAL_RESULTS_PATH",
    "SERVICE_ACCOUNT_PATH",
    "GCS_BUCKET",
    "VERTEX_PROJECT",
    "VERTEX_LOCATION",
    "VERTEX_MODEL",
    "NOPECHA_KEY",
    "RAPIDAPI_KEY",
    "FILEMAKER_BASIC_AUTH",
    "FILEMAKER_BEARER_TOKEN",
    "FILEMAKER_COUNTY_ID",
    "GOOGLE_SEARCH_RAPIDAPI_HOST",
    "ZILLOW_RAPIDAPI_HOST",
    "CHROME_EXTENSION_DIR",
    "ensure_directories",
]
