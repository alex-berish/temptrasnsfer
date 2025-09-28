import requests
import re

from settings import (
    MANUAL_JSON_PATH,
    RAPIDAPI_KEY,
    GOOGLE_SEARCH_RAPIDAPI_HOST,
    ZILLOW_RAPIDAPI_HOST,
)
from utils import read_json, write_json


# Function to perform Google search for the property address
def get_google_data(property_address):
    print(f"Performing Google search for property address: {property_address}")
    query_search = property_address.replace(" ", "+")
    if not RAPIDAPI_KEY:
        print("PIPELINE_RAPIDAPI_KEY is not set; cannot query RapidAPI for Google results.")
        return None

    search_url = f"https://{GOOGLE_SEARCH_RAPIDAPI_HOST}/"
    querystring = {
        "query": query_search + " site:zillow.com",
        "limit": "10",
        "related_keywords": "true",
    }
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": GOOGLE_SEARCH_RAPIDAPI_HOST,
    }
    response = requests.get(search_url, headers=headers, params=querystring)

    if response.status_code == 200:
        search_results = response.json()
        try:
            zillow_url = next(
                result["url"]
                for result in search_results["results"]
                if "zillow.com" in result["url"]
            )
            zpid_match = re.search(r"/(\d+)_zpid", zillow_url)
            zpid = zpid_match.group(1) if zpid_match else None
            print(f"Found Zillow URL: {zillow_url}, ZPID: {zpid}")
            return zillow_url, zpid
        except (KeyError, IndexError, StopIteration) as e:
            print(f"Error retrieving Zillow URL or ZPID: {e}")
            return None
    else:
        print(f"Google search request failed with status code: {response.status_code}")
        return None


# Function to fetch Zillow data for the given ZPID
def get_zillow_data(zpid):
    if not zpid:
        print("ZPID is missing, cannot fetch Zillow data.")
        return None

    print(f"Fetching Zillow data for ZPID: {zpid}")
    if not RAPIDAPI_KEY:
        print("PIPELINE_RAPIDAPI_KEY is not set; cannot query RapidAPI for Zillow data.")
        return None

    property_url = f"https://{ZILLOW_RAPIDAPI_HOST}/property"
    property_headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": ZILLOW_RAPIDAPI_HOST,
    }
    property_params = {"zpid": zpid}

    property_response = requests.get(
        property_url, headers=property_headers, params=property_params
    )

    if property_response.status_code == 200:
        property_data = property_response.json()
        print(f"Received full Zillow data for ZPID {zpid}")
        return property_data
    else:
        print(
            f"Failed to retrieve property details from Zillow API for ZPID: {zpid}. Status code: {property_response.status_code}"
        )
        return None

if __name__ == "__main__":
    try:
        data = read_json(MANUAL_JSON_PATH)
    except Exception as exc:
        print(f"Unable to read manual.json: {exc}")
        raise

    # Iterate over each entry in the data
    for entry in data:
        print(
            f"Processing entry with CaseNumber_Foreclosure: {entry.get('CaseNumber_Foreclosure')}"
        )

        # Skip if the entry already has ARV_PRISM
        if "ARV_PRISM" in entry:
            print("Entry already has ARV_PRISM. Skipping.")
            continue

        # Extract address details
        street = entry.get("Address_PRISM")
        city = entry.get("AddressCity_PRISM")
        state = entry.get("AddressState_PRISM")
        zip_code = entry.get("AddressZip_PRISM")
        print(f"Extracted address: {street}, {city}, {state} {zip_code}")

        if not all([street, city, state, zip_code]):
            print("Incomplete address information. Skipping.")
            continue

        property_address = f"{street}, {city}, {state} {zip_code}"

        # Get Google search data
        google_data = get_google_data(property_address)
        if google_data is None:
            print(
                f"Failed to retrieve Google data for address: {property_address}. Skipping."
            )
            continue

        zillow_url, zpid = google_data
        print(f"Retrieved Zillow URL: {zillow_url}, ZPID: {zpid}")

        # Get Zillow data
        zillow_data = get_zillow_data(zpid)
        if zillow_data is None:
            print(f"Failed to retrieve Zillow data for ZPID: {zpid}. Skipping.")
            continue

        # Now, extract the required fields from the full Zillow data and update the entry
        zestimate = zillow_data.get("zestimate")
        bedrooms = zillow_data.get("bedrooms")
        bathrooms = zillow_data.get("bathrooms")
        living_area = zillow_data.get("livingArea")
        rent_zestimate = zillow_data.get("rentZestimate")

        # Update entry with Zillow data
        entry.update(
            {
                "Zillow_PRISM": zestimate,  # Zestimate from Zillow API
                "ARV_PRISM": zestimate,  # Same as Zillow_PRISM
                "Beds_PRISM": bedrooms,  # Number of bedrooms from Zillow API
                "Baths_PRISM": bathrooms,  # Number of bathrooms from Zillow API
                "SqFootage_PRISM": living_area,  # Living area from Zillow API
                "Rent_PRISM": rent_zestimate,  # Rent Zestimate from Zillow API
                "ZillowLink_PRISM": zillow_url,  # Zillow URL
                "Additional_Zillow_Data": zillow_data,  # The full Zillow data response as nested JSON
            }
        )

    # Save the updated data back to the JSON file
    write_json(MANUAL_JSON_PATH, data, indent=4)

    print("Script completed and manual.json updated with Zillow data.")
