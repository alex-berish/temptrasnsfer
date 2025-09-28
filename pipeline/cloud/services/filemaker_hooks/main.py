"""Invoke FileMaker Start/Finish APIs from Cloud Run."""

from __future__ import annotations

import os

import requests

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from settings import FILEMAKER_COUNTY_ID

FILEMAKER_BEARER = os.environ.get("FILEMAKER_BEARER_TOKEN") or os.environ.get("FILEMAKER_BEARER")
ACTION = os.environ.get("ACTION", "start")  # start|finish
STATUS = os.environ.get("STATUS", "In progress")

BASE_URL = "https://fms.flippingmiracles.com/fmi/data/vLatest/databases/Api_Handshake_V1/layouts/Api_Handshake/script"


def build_url() -> str:
    script_name = "Start_Import_API" if ACTION == "start" else "Finish_Import_API"
    return f"{BASE_URL}/{script_name}"


def run() -> None:
    if not FILEMAKER_BEARER:
        raise RuntimeError("FileMaker bearer token not provided (set FILEMAKER_BEARER_TOKEN)")

    params = {
        "script.param": (
            f'{{"CountyID":"{FILEMAKER_COUNTY_ID}","Status":"{STATUS}"}}'
        )
    }
    headers = {"Authorization": f"Bearer {FILEMAKER_BEARER}", "Content-Type": "application/json"}
    resp = requests.get(build_url(), params=params, headers=headers, timeout=60)
    resp.raise_for_status()
    print(resp.text)


if __name__ == "__main__":
    run()
