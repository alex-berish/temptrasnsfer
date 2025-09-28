"""Cloud Run entrypoint for Vertex AI processing."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud import storage

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from settings import VERTEX_MODEL, VERTEX_PROJECT, VERTEX_LOCATION

PROMPT_BUCKET = os.environ["PROMPT_BUCKET"]
SUMMARY_BUCKET = os.environ.get("SUMMARY_BUCKET", PROMPT_BUCKET)
MODEL_NAME = os.environ.get("MODEL_NAME", VERTEX_MODEL)

GENERATION_CONFIG = {
    "max_output_tokens": 8192,
    "temperature": 0,
    "top_p": 0.95,
    "response_mime_type": "application/json",
}


def run() -> None:
    storage_client = storage.Client()
    vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
    model = GenerativeModel(MODEL_NAME)

    prompts_bucket = storage_client.bucket(PROMPT_BUCKET)
    summaries_bucket = storage_client.bucket(SUMMARY_BUCKET)

    for blob in prompts_bucket.list_blobs(prefix="prompts/"):
        if not blob.name.endswith("combination_text.txt"):
            continue
        case_id = Path(blob.name).parents[0].name
        prompt_text = blob.download_as_text()

        response = model.generate_content([prompt_text], generation_config=GENERATION_CONFIG, stream=False)
        output_blob = summaries_bucket.blob(f"summaries/{case_id}.json")
        output_blob.upload_from_string(response.text, content_type="application/json")
        print(f"Wrote summary for {case_id}")


if __name__ == "__main__":
    run()
