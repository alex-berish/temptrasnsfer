import requests
import urllib.parse
import uuid

from settings import MANUAL_JSON_PATH
from utils import read_json, write_json


# Function to generate the exact headers used in the valid request
def generate_headers():
    return {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,no;q=0.7,sv;q=0.6",
        "cache-control": "no-cache",
        "expires": "Sat, 01 Jan 2000 00:00:00 GMT",
        "origin": "https://ocpaweb.ocpafl.org",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://ocpaweb.ocpafl.org/",
        "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "x-user-key": str(uuid.uuid4()),  # Random UUID for x-user-key
    }


# Function to convert parcelId to TaxID
def parcel_id_to_tax_id(parcel_id):
    parcel_id_str = str(parcel_id)
    # Extract segments from parcel_id
    segment1 = parcel_id_str[:2]
    segment2 = parcel_id_str[2:4]
    segment3 = parcel_id_str[4:6]
    segment4 = parcel_id_str[6:10]
    segment5 = parcel_id_str[10:12]
    segment6 = parcel_id_str[12:]
    # Format as TaxID with reversed first three segments
    return f"{segment3}-{segment2}-{segment1}-{segment4}-{segment5}-{segment6}"


if __name__ == "__main__":

    # Load the JSON data from the file
    try:
        data = read_json(MANUAL_JSON_PATH)
    except Exception as exc:
        print(f"Unable to read manual.json: {exc}")
        raise

    # Base URLs for the API endpoints
    search_base_url = "https://ocpa-mainsite-afd-standard.azurefd.net/api/QuickSearch/GetSearchInfoByAddress"
    legal_desc_base_url = (
        "https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCPropFeatLegal"
    )
    general_info_base_url = (
        "https://ocpa-mainsite-afd-standard.azurefd.net/api/PRC/GetPRCGeneralInfo"
    )

    # Iterate over each JSON object in the data
    for entry in data:
        address = entry.get("Address_PRISM")

        if not address:
            continue  # Skip if there is no address

        # Encode the address for use in the URL
        encoded_address = urllib.parse.quote(address)

        # Construct the full URL with encoded parameters
        search_url = f"{search_base_url}?address={encoded_address}&page=1&size=5&sortBy=ParcelID&sortDir=ASC"

        # Generate headers for each request
        headers = generate_headers()

        try:
            # Send GET request to the API with exact headers
            response = requests.get(search_url, headers=headers)

            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                response_data = response.json()

                # If we get a valid response and "ownerName" and "parcelId" exist, update the JSON object
                if (
                    response_data
                    and "ownerName" in response_data[0]
                    and "parcelId" in response_data[0]
                ):
                    owner_name = response_data[0]["ownerName"]
                    parcel_id = response_data[0]["parcelId"]
                    print(f"Owner Name: {owner_name}, Parcel ID: {parcel_id}")

                    # Update the CountyDBName_PRISM field
                    entry["CountyDBName_PRISM"] = (
                        owner_name.strip()
                    )  # Remove any leading/trailing whitespace

                    # Create link https://ocpaweb.ocpafl.org/parcelsearch/Parcel%20ID/{parcelId}
                    entry["ParcelLink_PRISM"] = f"https://ocpaweb.ocpafl.org/parcelsearch/Parcel%20ID/{parcel_id}"

                    # Convert parcelId to TaxID
                    tax_id = parcel_id_to_tax_id(parcel_id)
                    print(f"Tax ID: {tax_id}")
                    entry["TaxID_PRISM"] = tax_id

                    # Fetch the property general info using the parcelId
                    general_info_url = f"{general_info_base_url}?pid={parcel_id}"
                    general_info_response = requests.get(general_info_url, headers=headers)

                    if general_info_response.status_code == 200:
                        general_info_data = general_info_response.json()
                        if (
                            "dorCode" in general_info_data
                            and "dorDescription" in general_info_data
                        ):
                            property_type = f"{general_info_data['dorCode']} - {general_info_data['dorDescription']}"
                            entry["PropertyType_PRISM"] = (
                                property_type.strip()
                            )  # Combine and remove any leading/trailing whitespace
                    else:
                        print(
                            f"Failed to fetch general info for parcelId: {parcel_id}. Status Code: {general_info_response.status_code}"
                        )

                    # Fetch the property legal description using the parcelId
                    legal_desc_url = f"{legal_desc_base_url}?pid={parcel_id}"
                    legal_desc_response = requests.get(legal_desc_url, headers=headers)

                    if legal_desc_response.status_code == 200:
                        legal_desc_data = legal_desc_response.json()
                        if "propertyDescription" in legal_desc_data:
                            entry["LegalDescription_PRISM"] = legal_desc_data[
                                "propertyDescription"
                            ].strip()  # Remove any leading/trailing whitespace
                    else:
                        print(
                            f"Failed to fetch legal description for parcelId: {parcel_id}. Status Code: {legal_desc_response.status_code}"
                        )

            else:
                print(
                    f"Failed to fetch data for address: {address}. Status Code: {response.status_code}"
                )

        except requests.RequestException as e:
            print(f"Error while fetching data for address: {address}. Error: {e}")

    # Save the updated data back to the JSON file
    write_json(MANUAL_JSON_PATH, data, indent=4)

    print("Script completed and manual.json updated.")
