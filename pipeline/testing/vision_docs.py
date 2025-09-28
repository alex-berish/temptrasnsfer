import os
from pathlib import Path
from google.cloud import vision
from google.cloud import storage
from google.oauth2 import service_account
import re
import json

from settings import (
    CASE_DOCS_DIR,
    OUTPUT_DIR,
    SERVICE_ACCOUNT_PATH,
    GCS_BUCKET,
    ensure_directories,
)


def async_detect_document(local_source_file, local_destination_dir):
    """OCR with PDF/TIFF as source files locally"""

    # Set up authentication
    local_source_file = Path(local_source_file)
    local_destination_dir = Path(local_destination_dir)

    credentials = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_PATH)
    )
    client = vision.ImageAnnotatorClient(credentials=credentials)

    mime_type = "application/pdf"
    batch_size = 30
    feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)

    # Upload local file to GCS for processing
    storage_client = storage.Client(credentials=credentials)
    bucket_name = GCS_BUCKET

    source_blob_name = f"input/{local_source_file.name}"
    destination_blob_name = f"output/{local_source_file.name}"

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)

    # Upload the file
    print(f"Uploading {local_source_file} to GCS bucket {bucket_name}")
    blob.upload_from_filename(str(local_source_file), timeout=600)
    gcs_source_uri = f"gs://{bucket_name}/{source_blob_name}"
    gcs_destination_uri = f"gs://{bucket_name}/{destination_blob_name}"

    gcs_source = vision.GcsSource(uri=gcs_source_uri)
    input_config = vision.InputConfig(gcs_source=gcs_source, mime_type=mime_type)

    gcs_destination = vision.GcsDestination(uri=gcs_destination_uri)
    output_config = vision.OutputConfig(
        gcs_destination=gcs_destination, batch_size=batch_size
    )

    async_request = vision.AsyncAnnotateFileRequest(
        features=[feature], input_config=input_config, output_config=output_config
    )

    operation = client.async_batch_annotate_files(requests=[async_request])

    print("Waiting for the operation to finish.")
    operation.result(timeout=8200)

    # Once the request has completed and the output has been
    # written to GCS, we can list all the output files.
    match = re.match(r"gs://([^/]+)/(.+)", gcs_destination_uri)
    bucket_name = match.group(1)
    prefix = match.group(2)

    bucket = storage_client.get_bucket(bucket_name)

    # List objects with the given prefix, filtering out folders.
    blob_list = [
        blob
        for blob in list(bucket.list_blobs(prefix=prefix))
        if not blob.name.endswith("/")
    ]
    print("Output files:")
    for blob in blob_list:
        print(blob.name)

    # Download the output files locally
    local_destination_dir.mkdir(parents=True, exist_ok=True)

    for blob in blob_list:
        local_output_file = local_destination_dir / os.path.basename(blob.name)
        blob.download_to_filename(str(local_output_file))
        print(f"Downloaded {blob.name} to {local_output_file}")

        all_text = ""
        # Process each output file
        with open(local_output_file, "r", encoding="utf-8") as f:
            response = json.load(f)
            for res in response["responses"]:
                if "fullTextAnnotation" in res:
                    all_text += res["fullTextAnnotation"]["text"] + "\n"

        # Save the concatenated full text from all pages to a file
        document_name = local_source_file.stem
        text_output_file = local_destination_dir / f"{document_name}_extracted_text.txt"
        with open(text_output_file, "a", encoding="utf-8") as f:
            f.write(all_text)
        print(f"Text from {local_output_file} has been appended to {text_output_file}")


def process_all_pdfs_in_directory(base_dir, output_base_dir):
    # Iterate through all case directories
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".pdf") and ("Complaint" in file or "Value" in file):
                case_number = os.path.basename(root)
                local_source_file = Path(root) / file
                local_destination_dir = Path(output_base_dir) / case_number

                print(f"Processing file: {local_source_file}")
                async_detect_document(local_source_file, local_destination_dir)


if __name__ == "__main__":
    ensure_directories()
    process_all_pdfs_in_directory(CASE_DOCS_DIR, OUTPUT_DIR)
