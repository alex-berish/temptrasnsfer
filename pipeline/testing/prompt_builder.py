import os
from pathlib import Path
from datetime import timedelta, datetime

from settings import OUTPUT_DIR, ensure_directories

def create_combination_text(output_base_dir):
    for root, dirs, files in os.walk(output_base_dir):
        root_path = Path(root)
        complaint_text = ""
        value_text = ""
        case_number = root_path.name

        # Read the text from the appropriate files
        for file in files:
            if "Complaint" in file and file.endswith("_extracted_text.txt"):
                with open(root_path / file, "r", encoding="utf-8") as f:
                    complaint_text = f.read().strip()
            elif "Value" in file and file.endswith("_extracted_text.txt"):
                with open(root_path / file, "r", encoding="utf-8") as f:
                    value_text = f.read().strip()

        if complaint_text or value_text:
            # Create the combination_text content
            combined_text = f"{complaint_text}\n\n\n{value_text}\n\n"
            today = datetime.now()
            yesterday = today - timedelta(days=1)
            formatted_yesterday = yesterday.strftime("%m/%d/%Y")
            formatted_today = today.strftime("%Y/%m/%d")
            json_template = (
                f"{combined_text}"
                "The text above was extracted via OCR from PDFs of either a complaint filing in Florida courts, or the complaint filing as well as a Value of Real Property filing, please fill out the following JSON object using the data. YOU MUST leave pre-filled fields as they are, and values you cannot find should be empty strings, not null. Your response should NOT contain markdown.\n\n"
                "{\n"
                '    "Address_PRISM": "", // The address of the foreclosed property as found in the document. This MUST be the address that is subject of the filing, NOT the mailing address of the defendant. It should not contain the city, state, or zip code.\n'
                '    "AddressCity_PRISM": "", // The city of the property address\n'
                '    "AddressState_PRISM": "FL", // Always "FL"\n'
                '    "AddressZip_PRISM": "", // Always 5 digits\n'
                '    "County_PRISM": "Orange", // Always "Orange"\n'
                '    "Foreclosure_PRISM": "", // "YES" or "NO", if discernible from language (e.g. "foreclosure" or "lien")\n'
                '    "Deceased_PRISM": "", // "LIVE" or "DECEASED", if discernible from language (e.g. "the late John Doe" or "the estate of John Doe") HOWEVER: Note that this must be the decased status of the PRIMARY DEFENDANT. If the document indicates someone has died, this is not necessarily "DECEASED" UNLESS it says the primary defendant died or says the primary defendant is an estate. Oftentimes a document will say a spouse died and the living spouse is named as the primary defendant ("LIVE" in that case)\n'
                '    "FirstName_Contacts": "", // The first name of the primary defendant / debtor\n'
                '    "LastName_Contacts": "", // The last name of the primary defendant / debtor\n'
                '    "Type_expenses": "", // Usually "Lien"\n'
                '    "ForeclosureType_PRISM": "", // Usually "Residential", a very small percent of the time it will be "Commercial Type 1" (standard commercial properties), "Quiet Title", "Partition Action", "Declaratory relief / easement", or "Timeshare", read the document to decide which.\n'
                '    "Cost_expenses": "", // This is a currency, but should be stored without commas or dollar signs, decimals are acceptable - extract from the Real Value of Property doc, the "Total Estimated Value of Claim" IF PROVIDED, otherwise leave blank\n'
                '    "PlaintiffType_PRISM": "", // "HOA", "BANK", or "PRIVATE". "HOA" if it is a Homeowners Association as the plaintiff, "Bank" if it is a bank or lender, "Private" if the plaintiff is named as a person or private company.\n'
                "}"
            )

            # Write the combined text and JSON template to a new file
            output_file_path = root_path / "combination_text.txt"
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(json_template)
            print(f"Created combination_text.txt in {root_path}")


if __name__ == "__main__":
    ensure_directories()
    create_combination_text(OUTPUT_DIR)
