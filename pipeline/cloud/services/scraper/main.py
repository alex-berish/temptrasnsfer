"""Cloud Run entrypoint for the Selenium scraper."""

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

from LOCAL_oc_records_search import main as local_scraper_main  # type: ignore

RAW_BUCKET = os.environ.get("RAW_BUCKET")
OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX", "raw_cases")


def upload_manifest(client: storage.Client, manifest: dict) -> None:
    if not RAW_BUCKET:
        print("RAW_BUCKET not set; skipping manifest upload")
        return

    bucket = client.bucket(RAW_BUCKET)
    blob = bucket.blob(f"{OUTPUT_PREFIX}/manifest.json")
    blob.upload_from_string(json.dumps(manifest, indent=2), content_type="application/json")
    print(f"Uploaded manifest to gs://{RAW_BUCKET}/{OUTPUT_PREFIX}/manifest.json")


def upload_case_artifacts(client: storage.Client, base_dir: Path) -> list[dict]:
    if not RAW_BUCKET:
        raise RuntimeError("RAW_BUCKET environment variable is required")

    bucket = client.bucket(RAW_BUCKET)
    manifest_cases: list[dict] = []

    for case_dir in sorted(base_dir.iterdir()):
        if not case_dir.is_dir():
            continue

        case_entry = {"case_number": case_dir.name, "files": []}
        for file_path in sorted(case_dir.glob("*")):
            if not file_path.is_file():
                continue
            destination_blob = f"{OUTPUT_PREFIX}/cases/{case_dir.name}/{file_path.name}"
            bucket.blob(destination_blob).upload_from_filename(file_path)
            case_entry["files"].append(
                {
                    "name": file_path.name,
                    "gcs_path": destination_blob,
                }
            )
        manifest_cases.append(case_entry)

    return manifest_cases


def run() -> None:
    client = storage.Client()

    # Run the existing local scraper in cloud environment.
    os.environ.setdefault("TMPDIR", "/tmp")
    local_scraper_main()

    case_docs_dir = Path(__file__).resolve().parents[2] / "case_docs"
    manifest_cases = upload_case_artifacts(client, case_docs_dir)
    manifest = {"cases": manifest_cases}
    upload_manifest(client, manifest)


if __name__ == "__main__":
    run()
