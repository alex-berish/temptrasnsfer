"""Upload the aggregated manual.json records into Firestore."""

from google.cloud import firestore

from settings import SERVICE_ACCOUNT_PATH, MANUAL_JSON_PATH
from utils import read_json


def upload_documents_to_firestore(documents):
    collection_name = "data_from_oc_records_search"
    db = firestore.Client.from_service_account_json(str(SERVICE_ACCOUNT_PATH))

    for document in documents:
        case_number = document["CaseNumber_Foreclosure"]
        db.collection(collection_name).document(case_number).set(document)
        print(f"Document {case_number} uploaded successfully")


if __name__ == "__main__":
    try:
        documents = read_json(MANUAL_JSON_PATH)
        upload_documents_to_firestore(documents)
        print("Documents uploaded successfully")
    except Exception as exc:
        print(f"Document upload failed: {exc}")
        raise
