"""Enrich case records with county appraiser data."""

from __future__ import annotations

import json
import os
import sys
from typing import List
from pathlib import Path

import requests
from google.cloud import storage

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTING_DIR = REPO_ROOT / "testing"
if str(TESTING_DIR) not in sys.path:
    sys.path.insert(0, str(TESTING_DIR))

from get_appraiser_data import generate_headers, parcel_id_to_tax_id  # type: ignore

SUMMARY_BUCKET = os.environ["SUMMARY_BUCKET"]
ENRICHED_BUCKET = os.environ.get("ENRICHED_BUCKET", SUMMARY_BUCKET)
OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX", "enriched")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "0"))

SEARCH_BASE_URL = "https://ocpa-mainsite-afd-standard.azurefd.net/api/QuickSearch/GetSearchInfoByAddress"
LEGAL_DESC_BASE_URL = "https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCPropFeatLegal"
GENERAL_INFO_BASE_URL = "https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCGeneralInfo"


def load_cases(client: storage.Client) -> List[dict]:
    bucket = client.bucket(SUMMARY_BUCKET)
    cases: List[dict] = []
    for blob in bucket.list_blobs(prefix="summaries/"):
        if blob.name.endswith(".json"):
            cases.append(json.loads(blob.download_as_text()))
            if BATCH_SIZE and len(cases) >= BATCH_SIZE:
                break
    return cases


def fetch_search_results(address: str, headers: dict) -> dict | None:
    encoded_address = requests.utils.quote(address)
    search_url = (
        f"{SEARCH_BASE_URL}?address={encoded_address}&page=1&size=5&sortBy=ParcelID&sortDir=ASC"
    )
    response = requests.get(search_url, headers=headers, timeout=30)
    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, list):
            return data[0]
    else:
        print(f"Search API failed for address '{address}' (status {response.status_code})")
    return None


def fetch_general_info(parcel_id: str, headers: dict) -> dict | None:
    url = f"{GENERAL_INFO_BASE_URL}?pid={parcel_id}"
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 200:
        return response.json()
    print(f"General info API failed for parcel {parcel_id} (status {response.status_code})")
    return None


def fetch_legal_description(parcel_id: str, headers: dict) -> dict | None:
    url = f"{LEGAL_DESC_BASE_URL}?pid={parcel_id}"
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 200:
        return response.json()
    print(f"Legal description API failed for parcel {parcel_id} (status {response.status_code})")
    return None


def enrich_case(entry: dict) -> dict:
    address = entry.get("Address_PRISM")
    if not address:
        entry.setdefault("AppraiserStatus", "SKIPPED_MISSING_ADDRESS")
        return entry

    headers = generate_headers()
    search_data = fetch_search_results(address, headers)
    if not search_data:
        entry.setdefault("AppraiserStatus", "NO_SEARCH_RESULT")
        return entry

    owner_name = search_data.get("ownerName")
    parcel_id = search_data.get("parcelId")
    if owner_name:
        entry["CountyDBName_PRISM"] = owner_name.strip()
    if parcel_id:
        entry["ParcelLink_PRISM"] = f"https://ocpaweb.ocpafl.org/parcelsearch/Parcel%20ID/{parcel_id}"
        entry["TaxID_PRISM"] = parcel_id_to_tax_id(parcel_id)

        general_info = fetch_general_info(parcel_id, headers)
        if general_info and "dorCode" in general_info and "dorDescription" in general_info:
            entry["PropertyType_PRISM"] = f"{general_info['dorCode']} - {general_info['dorDescription']}".strip()

        legal_info = fetch_legal_description(parcel_id, headers)
        if legal_info and "propertyDescription" in legal_info:
            entry["LegalDescription_PRISM"] = legal_info["propertyDescription"].strip()

    entry.setdefault("AppraiserStatus", "SUCCESS")
    return entry


def upload_cases(client: storage.Client, cases: list[dict]) -> None:
    bucket = client.bucket(ENRICHED_BUCKET)
    for entry in cases:
        case_number = entry.get("CaseNumber_Foreclosure", "unknown")
        blob = bucket.blob(f"{OUTPUT_PREFIX}/{case_number}.json")
        blob.upload_from_string(json.dumps(entry, indent=2), content_type="application/json")
        print(f"Uploaded enriched record for {case_number}")


def run() -> None:
    client = storage.Client()
    cases = load_cases(client)
    enriched = [enrich_case(entry) for entry in cases]
    upload_cases(client, enriched)


if __name__ == "__main__":
    run()
