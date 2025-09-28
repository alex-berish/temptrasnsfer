"""Cloud entrypoint for building prompt files."""

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

from prompt_builder import create_combination_text

OCR_BUCKET = os.environ["OCR_BUCKET"]
PROMPT_BUCKET = os.environ.get("PROMPT_BUCKET", OCR_BUCKET)
CASE_LIST_PATH = os.environ["CASE_LIST_PATH"]
WORKDIR = Path("/tmp/prompts")


def fetch_case_list(client: storage.Client) -> list[str]:
    if CASE_LIST_PATH.startswith("gs://"):
        _, rest = CASE_LIST_PATH.split("gs://", 1)
        bucket_name, blob_name = rest.split("/", 1)
        blob = client.bucket(bucket_name).blob(blob_name)
        case_manifest = json.loads(blob.download_as_text())
        return case_manifest.get("cases", [])
    raise ValueError("CASE_LIST_PATH must be a gs:// URI")


def sync_ocr_files(client: storage.Client, case_ids: list[str]) -> Path:
    WORKDIR.mkdir(parents=True, exist_ok=True)
    source_bucket = client.bucket(OCR_BUCKET)
    for case_id in case_ids:
        dest_case_dir = WORKDIR / case_id
        dest_case_dir.mkdir(exist_ok=True)
        prefix = f"ocr/{case_id}/"
        for blob in source_bucket.list_blobs(prefix=prefix):
            if blob.name.endswith("_extracted_text.txt"):
                destination = dest_case_dir / Path(blob.name).name
                blob.download_to_filename(destination)
    return WORKDIR


def upload_prompts(client: storage.Client) -> None:
    dest_bucket = client.bucket(PROMPT_BUCKET)
    for file_path in WORKDIR.rglob("combination_text.txt"):
        blob = dest_bucket.blob(f"prompts/{file_path.relative_to(WORKDIR)}")
        blob.upload_from_filename(file_path)


def run() -> None:
    client = storage.Client()
    case_ids = fetch_case_list(client)
    sync_ocr_files(client, case_ids)
    create_combination_text(WORKDIR)
    upload_prompts(client)


if __name__ == "__main__":
    run()
