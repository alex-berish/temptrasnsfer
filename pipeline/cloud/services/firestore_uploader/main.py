"""Upload final case records from GCS into Firestore."""

from __future__ import annotations

import json
import os

from google.cloud import firestore, storage

FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "data_from_oc_records_search")
ZILLOW_BUCKET = os.environ["ZILLOW_BUCKET"]
PREFIX = os.environ.get("ZILLOW_PREFIX", "zillow/")


def load_records(client: storage.Client) -> list[dict]:
    bucket = client.bucket(ZILLOW_BUCKET)
    return [
        json.loads(blob.download_as_text())
        for blob in bucket.list_blobs(prefix=PREFIX)
        if blob.name.endswith(".json")
    ]


def upload(records: list[dict]) -> None:
    db = firestore.Client()
    for entry in records:
        case_number = entry["CaseNumber_Foreclosure"]
        db.collection(FIRESTORE_COLLECTION).document(case_number).set(entry)
        print(f"Uploaded {case_number}")


def run() -> None:
    storage_client = storage.Client()
    records = load_records(storage_client)
    upload(records)


if __name__ == "__main__":
    run()
