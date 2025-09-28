"""Obtain a FileMaker session token using the configured Basic auth credentials."""

import requests

from settings import FILEMAKER_BASIC_AUTH

URL = "https://fms.flippingmiracles.com/fmi/data/vLatest/databases/Api_Handshake_V1/sessions"


def request_token():
    if not FILEMAKER_BASIC_AUTH:
        raise RuntimeError("PIPELINE_FILEMAKER_BASIC is not set; cannot request FileMaker token.")

    headers = {
        "Authorization": f"Basic {FILEMAKER_BASIC_AUTH}",
        "Content-Type": "application/json",
    }

    response = requests.post(URL, headers=headers, json={})
    response.raise_for_status()
    print(response.text)


if __name__ == "__main__":
    request_token()
