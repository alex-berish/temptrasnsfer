"""Notify FileMaker that an import run has started."""

import requests

from settings import FILEMAKER_BEARER_TOKEN, FILEMAKER_COUNTY_ID

URL = (
    "https://fms.flippingmiracles.com/fmi/data/vLatest/databases/Api_Handshake_V1/"
    "layouts/Api_Handshake/script/Start_Import_API"
)


def mark_import_started(status: str = "In progress"):
    if not FILEMAKER_BEARER_TOKEN:
        raise RuntimeError("PIPELINE_FILEMAKER_BEARER is not set; cannot call FileMaker API.")

    params = {
        "script.param": (
            f'{{"CountyID":"{FILEMAKER_COUNTY_ID}","Status":"{status}"}}'
        )
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FILEMAKER_BEARER_TOKEN}",
    }

    response = requests.get(URL, headers=headers, params=params)
    response.raise_for_status()
    print(response.text)


if __name__ == "__main__":
    mark_import_started()
