"""Enrich cases with Zillow data using RapidAPI."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from google.cloud import storage

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTING_DIR = REPO_ROOT / "testing"
if str(TESTING_DIR) not in sys.path:
    sys.path.insert(0, str(TESTING_DIR))

from get_zillow_data import get_google_data, get_zillow_data  # type: ignore

ENRICHED_BUCKET = os.environ["ENRICHED_BUCKET"]
ZILLOW_BUCKET = os.environ.get("ZILLOW_BUCKET", ENRICHED_BUCKET)
OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX", "zillow")


def load_cases(client: storage.Client) -> list[dict]:
    bucket = client.bucket(ENRICHED_BUCKET)
    return [
        json.loads(blob.download_as_text())
        for blob in bucket.list_blobs(prefix="enriched/")
        if blob.name.endswith(".json")
    ]


def enrich_case(entry: dict) -> dict:
    address_parts = [
        entry.get("Address_PRISM"),
        entry.get("AddressCity_PRISM"),
        entry.get("AddressState_PRISM"),
        entry.get("AddressZip_PRISM"),
    ]
    if not all(address_parts):
        entry.setdefault("ZillowStatus", "SKIPPED_MISSING_ADDRESS")
        return entry

    property_address = ", ".join(address_parts[:3]) + f" {address_parts[3]}"
    google_result = get_google_data(property_address)
    if not google_result:
        entry.setdefault("ZillowStatus", "NO_GOOGLE_RESULT")
        return entry

    zillow_url, zpid = google_result
    zillow_data = get_zillow_data(zpid)
    if not zillow_data:
        entry.setdefault("ZillowStatus", "NO_ZILLOW_RESULT")
        return entry

    entry.update(
        {
            "Zillow_PRISM": zillow_data.get("zestimate"),
            "ARV_PRISM": zillow_data.get("zestimate"),
            "Beds_PRISM": zillow_data.get("bedrooms"),
            "Baths_PRISM": zillow_data.get("bathrooms"),
            "SqFootage_PRISM": zillow_data.get("livingArea"),
            "Rent_PRISM": zillow_data.get("rentZestimate"),
            "ZillowLink_PRISM": zillow_url,
            "Additional_Zillow_Data": zillow_data,
            "ZillowStatus": "SUCCESS",
        }
    )
    return entry


def upload_cases(client: storage.Client, cases: list[dict]) -> None:
    bucket = client.bucket(ZILLOW_BUCKET)
    for entry in cases:
        case_number = entry.get("CaseNumber_Foreclosure", "unknown")
        blob = bucket.blob(f"{OUTPUT_PREFIX}/{case_number}.json")
        blob.upload_from_string(json.dumps(entry, indent=2), content_type="application/json")
        print(f"Uploaded Zillow data for {case_number}")


def run() -> None:
    client = storage.Client()
    cases = load_cases(client)
    enriched = [enrich_case(entry) for entry in cases]
    upload_cases(client, enriched)


if __name__ == "__main__":
    run()
