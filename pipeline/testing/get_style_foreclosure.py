import re
from pathlib import Path

from settings import CASE_DOCS_DIR, MANUAL_JSON_PATH, ensure_directories
from utils import read_json, write_json


def clean_style(style):
    # Remove any leading/trailing whitespace
    style = style.strip()

    # Replace multiple spaces with a single space
    style = re.sub(r"\s+", " ", style)

    # Ensure "vs." is correctly formatted with proper spacing
    style = re.sub(r"(\w+)vs\.(\w+)", r"\1 vs. \2", style)

    # Ensure "et al" is correctly formatted with proper spacing
    style = re.sub(r"(\w+)et al", r"\1 et al", style)

    return style


def process_foreclosure_data(json_path: Path, directory_path: Path):
    print(f"Opening JSON file: {json_path}")
    try:
        data = read_json(json_path)
        print(f"Loaded {len(data)} items from JSON file")
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return

    updates_made = 0

    for item in data:
        case_number = item["CaseNumber_Foreclosure"]
        print(f"Processing case number: {case_number}")

        # Search for a matching directory
        matching_dirs = [
            d for d in directory_path.iterdir() if d.is_dir() and d.name.endswith(case_number[-6:])
        ]

        if matching_dirs:
            case_dir = matching_dirs[0]
            style_file = case_dir / "style_foreclosure.txt"
            print(f"Looking for style file: {style_file}")

            if style_file.is_file():
                try:
                    with style_file.open("r", encoding="utf-8") as f:
                        content = f.read().strip()
                    print(f"Content of style file: {content}")

                    match = re.search(r":\s*(.*)", content)
                    if match:
                        style = match.group(1)
                        print(f"Extracted style: {style}")

                        # Clean and format the style
                        style = clean_style(style)
                        print(f"Processed style: {style}")

                        # Always update the Style_foreclosure field
                        item["Style_foreclosure"] = style
                        updates_made += 1
                        print(f"Updated Style_foreclosure for case {case_number}")
                    else:
                        print(f"No match found in content for case {case_number}")
                except Exception as e:
                    print(f"Error processing style file for case {case_number}: {e}")
            else:
                print(f"Style file not found for case {case_number}")
        else:
            print(f"No matching directory found for case {case_number}")

    print(f"Total updates made: {updates_made}")

    if updates_made > 0:
        print(f"Writing updated data back to {json_path}")
        try:
            write_json(json_path, data, indent=2)
            print("File write completed successfully")
        except Exception as e:
            print(f"Error writing to JSON file: {e}")
    else:
        print("No updates were made, skipping file write")


if __name__ == "__main__":
    ensure_directories()
    process_foreclosure_data(MANUAL_JSON_PATH, CASE_DOCS_DIR)
