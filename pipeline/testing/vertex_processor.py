import os
import json
import datetime
import vertexai
from vertexai.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models
from google.api_core.exceptions import InternalServerError
import time
import re

from settings import (
    OUTPUT_DIR,
    MANUAL_JSON_PATH,
    SERVICE_ACCOUNT_PATH,
    VERTEX_PROJECT,
    VERTEX_LOCATION,
    VERTEX_MODEL,
    ensure_directories,
)

# Set the path to the service account JSON file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(SERVICE_ACCOUNT_PATH)

# Initialize the model and configurations

# set region to europe-west4


vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
model = GenerativeModel(VERTEX_MODEL)

generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0,
    "top_p": 0.95,
    "response_mime_type": "application/json",
}

safety_settings = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# Initialize a list to hold all outputs
all_outputs = []

# Get today's date in YYYY-MM-DD format
today_date = datetime.date.today().strftime("%Y-%m-%d")

# Iterate through each folder in the output directory
ensure_directories()
for case_path in OUTPUT_DIR.iterdir():
    if case_path.is_dir():
        case_folder = case_path.name
        combination_text_path = case_path / "combination_text.txt"
        if combination_text_path.exists():
            # Read the content from combination_text.txt
            with open(combination_text_path, "r") as file:
                content = file.read()

            try:
                # Generate content using the model with streaming set to False
                response = model.generate_content(
                    [content],
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                    stream=False,
                )
                print(f"Response content for case {case_folder}: {response.text}")

                # Clean the response text to extract JSON
                response_text = response.text.strip()
                cleaned_response = re.sub(
                    r"^```.*?```$", "", response_text, flags=re.DOTALL
                ).strip()

                # Assuming the response contains valid JSON data
                try:
                    generated_data = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    print(
                        f"Error decoding JSON for case {case_folder}: {cleaned_response}"
                    )
                    generated_data = {}

                output_dict = {
                    "FileDate_foreclosure": "",
                    "DATE.ProcessedByAI_Import": today_date,
                    "CaseNumber_Foreclosure": case_folder,
                    "CountyDBName_PRISM": "",
                    "LegalDescription_PRISM": "",
                    "TaxID_PRISM": "",
                    "Style_foreclosure": "",
                    "ProcessingCompleted": "True",
                    "PropertyType_PRISM": "",
                }

                # Merge the generated data with the output dictionary
                output_dict.update(generated_data)

                all_outputs.append(output_dict)

                # Print the final dictionary for each case
                print(f"Final output for case {case_folder}: {output_dict}")
                time.sleep(20)  # avoid rate limit

            except InternalServerError as e:
                print(f"Error processing case {case_folder}: {e}")

            #handle 429 too many requests
            except vertexai.preview.generative_models.GenerativeModelsRateLimitError as e:
                print(f"Rate limit error processing case {case_folder}: {e}")
                time.sleep(110)  # wait for 60 seconds
            except Exception as e:
                print(f"Error processing case {case_folder}: {e}")

# Write the collected outputs to the manual.json file
with MANUAL_JSON_PATH.open("w") as manual_file:
    json.dump(all_outputs, manual_file, indent=4)

print(f"Generated content has been saved to {MANUAL_JSON_PATH}")
