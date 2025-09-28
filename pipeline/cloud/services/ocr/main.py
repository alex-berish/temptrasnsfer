"""Cloud Run entrypoint for OCR processing."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict

from google.cloud import storage

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTING_DIR = REPO_ROOT / "testing"
if str(TESTING_DIR) not in sys.path:
    sys.path.insert(0, str(TESTING_DIR))

from vision_docs import process_all_pdfs_in_directory

RAW_BUCKET = os.environ["RAW_BUCKET"]
OCR_BUCKET = os.environ.get("OCR_BUCKET", RAW_BUCKET)
MANIFEST_PATH = os.environ["MANIFEST_PATH"]  # e.g., gs://bucket/raw_cases/manifest.json
WORKDIR = Path("/tmp/ocr")


def download_manifest(client: storage.Client) -> Dict:
    if not MANIFEST_PATH.startswith("gs://"):
        raise ValueError("MANIFEST_PATH must be a GCS URI")
    _, remainder = MANIFEST_PATH.split("gs://", 1)
    bucket_name, blob_name = remainder.split("/", 1)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    data = json.loads(blob.download_as_text())
    return data


def sync_case_data(client: storage.Client, manifest: Dict) -> Path:
    WORKDIR.mkdir(parents=True, exist_ok=True)
    for case_id in manifest.get("cases", []):
        case_dir = WORKDIR / case_id
        case_dir.mkdir(exist_ok=True)
        bucket = client.bucket(RAW_BUCKET)
        prefix = f"cases/{case_id}/"
        for blob in bucket.list_blobs(prefix=prefix):
            if blob.name.endswith(".pdf"):
                destination = case_dir / Path(blob.name).name
                destination.parent.mkdir(parents=True, exist_ok=True)
                blob.download_to_filename(destination)
    return WORKDIR


def upload_outputs(client: storage.Client) -> None:
    dest_bucket = client.bucket(OCR_BUCKET)
    for file_path in WORKDIR.rglob("*_extracted_text.txt"):
        blob = dest_bucket.blob(f"ocr/{file_path.relative_to(WORKDIR)}")
        blob.upload_from_filename(file_path)


def run() -> None:
    client = storage.Client()
    manifest = download_manifest(client)
    sync_case_data(client, manifest)
    process_all_pdfs_in_directory(WORKDIR, WORKDIR)
    upload_outputs(client)


if __name__ == "__main__":
    run()
