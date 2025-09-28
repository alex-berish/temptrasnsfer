"""Assign RECORD_ID fields to Firestore documents that do not have one."""

import os
import uuid

from google.cloud import firestore

from settings import SERVICE_ACCOUNT_PATH

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SERVICE_ACCOUNT_PATH)


def generate_record_id() -> str:
    return str(uuid.uuid4()).upper()


def assign_record_ids():
    db = firestore.Client()
    collections = db.collections()
    for collection in collections:
        for doc in collection.stream():
            doc_data = doc.to_dict()
            if "RECORD_ID" not in doc_data:
                record_id = generate_record_id()
                doc.reference.update({"RECORD_ID": record_id})
                print(f"Assigned RECORD_ID {record_id} to document {doc.id}")


if __name__ == "__main__":
    assign_record_ids()
    print("Finished assigning RECORD_IDs to all documents without one.")
