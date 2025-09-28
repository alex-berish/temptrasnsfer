import requests
import urllib.parse

from settings import MANUAL_JSON_PATH
from utils import read_json, write_json


# Function to generate the headers for API requests
def generate_headers():
    return {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,no;q=0.7,sv;q=0.6",
        "cache-control": "no-cache",
        "origin": "https://ocpaweb.ocpafl.org",
        "pragma": "no-cache",
        "referer": "https://ocpaweb.ocpafl.org/",
        "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }


# Function to perform GET request and return response as JSON
def fetch_data(url, headers):
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(
                f"Failed to fetch data from {url}. Status Code: {response.status_code}"
            )
            return None
    except requests.RequestException as e:
        print(f"Error fetching data from {url}: {e}")
        return None


# Function to build URLs for various APIs using parcelId
def build_urls(parcel_id):
    return {
        "GeneralInfo": f"https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCGeneralInfo?pid={parcel_id}",
        "Stats": f"https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCStats?PID={parcel_id}",
        "CertifiedTaxes": f"https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCCertifiedTaxes?PID={parcel_id}&TaxYear=0",
        "TotalTaxes": f"https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCTotalTaxes?PID={parcel_id}&TaxYear=0",
        "NonAdValorem": f"https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCNonAdValorem?PID={parcel_id}&TaxYear=0",
        "PropFeatBldg": f"https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCPropFeatBldg?pid={parcel_id}&page=1&size=5",
        "PropFeatLandArea": f"https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCPropFeatLandArea?pid={parcel_id}",
    }


# Function to fetch all data for a given parcelId and store it in Additional_Appraiser_Data
def fetch_and_store_additional_data(entry, parcel_id, headers):
    urls = build_urls(parcel_id)
    additional_data = {}

    for key, url in urls.items():
        data = fetch_data(url, headers)
        if data:
            additional_data[key] = data

    # Store the additional data in the entry under "Additional_Appraiser_Data"
    entry["Additional_Appraiser_Data"] = additional_data


# Function to fetch parcelId using the address from Address_PRISM
def fetch_parcel_id_by_address(address, headers):
    encoded_address = urllib.parse.quote(address)
    search_url = f"https://ocpa-mainsite-afd-standard.azurefd.net/api/QuickSearch/GetSearchInfoByAddress?address={encoded_address}&page=1&size=5&sortBy=ParcelID&sortDir=ASC"
    search_data = fetch_data(search_url, headers)

    if search_data and isinstance(search_data, list) and "parcelId" in search_data[0]:
        return search_data[0]["parcelId"]
    else:
        print(f"No parcelId found for address: {address}")
        return None

if __name__ == "__main__":

    # Load the JSON data from the file
    try:
        data = read_json(MANUAL_JSON_PATH)
    except Exception as exc:
        print(f"Unable to read manual.json: {exc}")
        raise

    # Iterate over each entry in the data
    for entry in data:
        headers = generate_headers()
        parcel_id = entry.get("parcelId")
        if parcel_id:
            print(f"Using existing parcelId: {parcel_id}")
        else:
            address = entry.get("Address_PRISM")
            # If an address exists, fetch the parcelId by address
            if address:
                parcel_id = fetch_parcel_id_by_address(address, headers)
                if parcel_id:
                    print(f"Fetched parcelId: {parcel_id} for address: {address}")

        # Fetch and store additional appraiser data if parcelId is available
        if parcel_id:
            fetch_and_store_additional_data(entry, parcel_id, headers)

    # Save the updated data back to the JSON file
    write_json(MANUAL_JSON_PATH, data, indent=4)

    print("Script completed and manual.json updated with Additional_Appraiser_Data.")
