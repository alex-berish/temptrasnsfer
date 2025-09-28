import json
import os
from pathlib import Path
import requests
import tempfile
import zipfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime, timedelta
import argparse
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv

from settings import (
    CASE_DOCS_DIR,
    CHROME_EXTENSION_DIR,
    ERROR_LOG_PATH,
    NOPECHA_KEY,
    ensure_directories,
)


# global variable to store processed cases
processed_cases = []

def configure_chrome_options(download_dir: str, extension: str | None = None):
    options = Options()
    if extension:
        options.add_argument(f"--disable-extensions-except={extension}")
        options.add_argument(f"--load-extension={extension}")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    prefs = {
        "download.default_directory": download_dir,
        "plugins.always_open_pdf_externally": True,
        "download.directory_upgrade": True,
        "download.prompt_for_download": False
    }
    options.add_experimental_option("prefs", prefs)
    return options

def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def unzip_file(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def edit_manifest(extension, key):
    manifest_path = Path(extension) / 'manifest.json'
    with manifest_path.open('r') as f:
        manifest = json.load(f)
    manifest['nopecha']['key'] = key
    with manifest_path.open('w') as f:
        json.dump(manifest, f, indent=4)

def download_extension(key, extension):
    if not key:
        print("PIPELINE_NOPECHA_KEY is not set. Running without the NopeCHA extension; be prepared to solve CAPTCHAs manually.")
        return
    url = 'https://github.com/NopeCHALLC/nopecha-extension/releases/latest/download/chromium_automation.zip'
    # Download and extract
    zip_path = 'chromium.zip'
    download_file(url, zip_path)
    unzip_file(zip_path, extension)
    # Edit manifest.json
    edit_manifest(extension, key)

def wait_for_captcha_to_be_solved(driver, timeout=120):
    time.sleep(5)  # Wait for the extension to open the iframe
    try:
        WebDriverWait(driver, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "iframe[title^='recaptcha challenge']"))
        )
    except TimeoutException:
        print("CAPTCHA was not solved in time")
        driver.quit()
        raise

# Function to extract links from the current page
def extract_links_from_page():
    case_links = []
    table = driver.find_element(By.ID, "caseList")
    rows = table.find_elements(By.TAG_NAME, "tr")
    for row in rows:
        try:
            case_number_cell = row.find_element(By.CLASS_NAME, "colCaseNumber")
            link_element = case_number_cell.find_element(By.TAG_NAME, "a")
            case_number = link_element.text
            case_links.append(case_number)
        except Exception as e:
            continue
    return case_links


def create_case_directory(case_number, download_dir):
    # Create subdirectory for the case if it doesn't exist
    subfolder_path = Path(download_dir) / case_number
    subfolder_path.mkdir(parents=True, exist_ok=True)
    return subfolder_path


def save_pdf(driver, download_dir, pdf_name, subfolder_path):
    # Path where Chrome downloads files by default
    temp_file_path = Path(download_dir) / "Doc.pdf"
    final_file_path = Path(subfolder_path) / f"{pdf_name}.pdf"

    # Wait for the file to download
    # Check for presence of the file and that it's no longer a partial download
    while not temp_file_path.exists() or temp_file_path.name.endswith(".crdownload"):
        time.sleep(1)  # Adjust sleep time if necessary for network conditions

    # Move the downloaded file to the specific case directory
    if temp_file_path.exists():
        temp_file_path.rename(final_file_path)
        print(f"PDF saved as {final_file_path}")
    else:
        print(f"Download failed or file not found: {temp_file_path}")


def log_error(case_number, message):
    error_log_path = ERROR_LOG_PATH

    try:
        if error_log_path.exists() and error_log_path.stat().st_size > 0:
            with error_log_path.open("r") as f:
                error_log = json.load(f)
            print(f"Loaded existing error log from {error_log_path}")
        else:
            error_log = {}
            print(f"Initialized new error log at {error_log_path}")
    except json.JSONDecodeError:
        error_log = {}
        print(f"Error decoding JSON from {error_log_path}. Initialized new error log.")

    error_log[case_number] = message
    print(f"Logged error for case {case_number}: {message}")

    with error_log_path.open("w") as f:
        json.dump(error_log, f, indent=4)
        print(f"Updated error log saved to {error_log_path}")


# Function to find and click the "Complaint" link
def process_complaint_link(driver, case_number, download_dir, retries=1):
    for attempt in range(retries):
        try:
            # Wait for the "Complaint" link to be clickable
            complaint_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Complaint')]"))
            )
            complaint_link.click()

            # Wait for the new tab to open
            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)

            # Switch to the new tab
            driver.switch_to.window(driver.window_handles[-1])

            # Check for error page
            if is_error_page(driver):
                print(f"Error page detected for {case_number}. Retry {attempt + 1} of {retries}")
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                continue

            # Save the PDF
            print(f"{case_number} it should be this")
            subfolder_path = create_case_directory(case_number, download_dir)
            save_pdf(driver, download_dir, case_number, subfolder_path=subfolder_path)

            # Switch back to the original tab
            driver.switch_to.window(driver.window_handles[0])
            break

        except Exception as e:
            log_error(case_number, f"Error processing complaint link: {e}")
            print(f"Error processing complaint link for {case_number} on attempt {attempt + 1}")
            # Ensure to close any extra tabs before retrying
            while len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
                driver.close()
            driver.switch_to.window(driver.window_handles[0])
            if attempt == retries - 1:
                print(f"Skipping {case_number} after {retries} attempts")


def process_document_link(
    driver, case_number, download_dir, link_text, pdf_name, subfolder_path, retries=1):
    
    for attempt in range(retries):
        try:
            # Wait for the link to be clickable
            document_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//a[contains(text(), '{link_text}')]")
                )
            )
            document_link.click()

            # Wait for the new tab to open
            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)

            # Switch to the new tab
            driver.switch_to.window(driver.window_handles[-1])

            # Check for error page
            if is_error_page(driver):
                print(
                    f"Error page detected for {case_number}. Retry {attempt + 1} of {retries}"
                )
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                continue

            # Save the PDF
            save_pdf(driver, download_dir, f"{pdf_name}_{case_number}", subfolder_path)

            # Switch back to the original tab
            driver.switch_to.window(driver.window_handles[0])
            break

        except Exception as e:
            log_error(case_number, f"Error processing {link_text} link: {e}")
            print(
                f"Error processing {link_text} link for {case_number} on attempt {attempt + 1}"
            )
            # Ensure to close any extra tabs before retrying
            time.sleep(1)
            while len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
                driver.close()
            driver.switch_to.window(driver.window_handles[0])
            if attempt == retries - 1:
                print(f"Skipping {case_number} after {retries} attempts")


def is_error_page(driver):
    try:
        error_element = driver.find_element(By.CSS_SELECTOR, ".panel-body h3.text-primary")
        if "Something unexpected happened" in error_element.text:
            return True
    except NoSuchElementException:
        return False
    return False


# Function to check for the "Next" button
def is_next_button_present(driver):
    try:
        # Locate the Next button
        next_button = driver.find_element(By.ID, "caseList_next")
        # Check if the button is not disabled
        is_disabled = "disabled" in next_button.get_attribute("class")
        return not is_disabled
    except NoSuchElementException:
        # If the button doesn't exist, return False
        return False


def extract_and_save_case_details(driver, subfolder_path, case_number):
    try:
        # Before extraction, log the current state of the driver
        print("Current URL before extraction:", driver.current_url)
        print("Number of windows before extraction:", len(driver.window_handles))

        # Locate the div with id 'caseHeader'
        case_header = driver.find_element(By.ID, "caseHeader")

        # Get the entire HTML content of 'caseHeader'
        inner_html = case_header.get_attribute("innerHTML")

        # Open a file in the subfolder to write the details
        details_path = Path(subfolder_path) / "case_details.txt"
        with details_path.open("w") as file:
            file.write(inner_html)

        print(f"Case details saved to {details_path}")

        # After extraction, log the final state of the driver
        print("Current URL after extraction:", driver.current_url)
        print("Number of windows after extraction:", len(driver.window_handles))

    except Exception as e:
        print(f"Failed to extract case details for case {case_number}: {e}")
        log_error(case_number, f"Failed to extract case details: {e}")


def extract_case_title(driver, subfolder_path, case_number):
    try:
        # Locate the div with id 'caseDetails'
        case_details_div = driver.find_element(By.ID, "caseDetails")

        # Locate the div with the class 'text-center panel-heading'
        case_title_div = case_details_div.find_element(
            By.CLASS_NAME, "text-center.panel-heading"
        )

        # save the case title to a file called "style_foreclosure.txt"
        case_title = case_title_div.text
        case_title_path = Path(subfolder_path) / "style_foreclosure.txt"
        with case_title_path.open("w") as file:
            file.write(case_title)
        
        print(f"Case title saved to {case_title_path}")

    except NoSuchElementException:
        print("Failed to locate case title element.")
        return None


def navigate_to_page(target_page):
    current_page = 1
    while current_page < target_page:
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Next')]"))
            )
            next_button.click()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "caseList"))
            )
            current_page += 1
            print(f"Moved to page {current_page}")
        except TimeoutException:
            print(f"Failed to navigate to page {current_page + 1}. Retrying...")
            continue


def extract_and_save_case_initiated_date(driver, subfolder_path):
    print("extract_and_save_case_initiated_date")
    try:
        # Find all elements that match the "Case Initiated" text
        elements = driver.find_elements(
            By.XPATH, "//*[contains(text(), 'Case Initiated')]"
        )
        for element in elements:
            print("Found Case Initiated element:", element.text)
            # Traverse to the parent row element
            parent_row = element.find_element(By.XPATH, "./ancestor::tr")
            print("Found parent row:", parent_row)
            # Find all child td elements within the parent row
            tds = parent_row.find_elements(By.TAG_NAME, "td")
            for i, td in enumerate(tds):
                if "Case Initiated" in td.text:
                    if i > 0:
                        # Get the date from the previous td element
                        date_td = tds[i - 1]
                        case_initiated_date = date_td.get_attribute(
                            "sorttable_customkey"
                        )
                        print("case_initiated_date:", case_initiated_date)

                        if case_initiated_date:
                            # Save the date to a text file in the subfolder path
                            date_file_path = Path(subfolder_path) / "case_initiated_date.txt"
                            with date_file_path.open("w") as date_file:
                                date_file.write(case_initiated_date)

                            print(f"Case initiated date saved to {date_file_path}")
                        else:
                            print("Case initiated date attribute not found.")
                            log_error(
                                "case_initiated",
                                "Case initiated date attribute not found.",
                            )
                    else:
                        print(
                            "Case Initiated is the first element, no preceding date found."
                        )
                    break
    except NoSuchElementException:
        log_error("case_initiated", "Case Initiated date not found")
        print("Case Initiated date not found")
    except Exception as e:
        log_error("case_initiated", f"Error extracting case initiated date: {e}")
        print(f"Error extracting case initiated date: {e}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run foreclosure scraper with optional date range override.")
    parser.add_argument("--date-from", dest="date_from", help="Start date in MM/DD/YYYY format")
    parser.add_argument("--date-to", dest="date_to", help="End date in MM/DD/YYYY format")
    return parser.parse_args()


def determine_dates(date_from_override: str | None, date_to_override: str | None) -> tuple[str, str]:
    if date_from_override and date_to_override:
        return date_from_override, date_to_override

    # Default logic as before
    if datetime.today().weekday() in [1, 2, 3, 4, 5]:
        date_from = (datetime.today() - timedelta(days=1)).strftime("%m/%d/%Y")
        date_to = datetime.today().strftime("%m/%d/%Y")
    elif datetime.today().weekday() == 0:
        date_from = (datetime.today() - timedelta(days=3)).strftime("%m/%d/%Y")
        date_to = (datetime.today() - timedelta(days=1)).strftime("%m/%d/%Y")
    else:
        # Weekend fallback: use Friday.
        date_from = (datetime.today() - timedelta(days=datetime.today().weekday() - 4)).strftime("%m/%d/%Y")
        date_to = (datetime.today() - timedelta(days=datetime.today().weekday() - 4)).strftime("%m/%d/%Y")
    return date_from, date_to


def main():
    args = parse_args()
    ensure_directories()

    download_dir = str(CASE_DOCS_DIR.resolve())
    extension_path = CHROME_EXTENSION_DIR.resolve()

    extension_path.mkdir(parents=True, exist_ok=True)
    download_extension(NOPECHA_KEY, str(extension_path))

    extension_arg = str(extension_path) if NOPECHA_KEY else None
    options = configure_chrome_options(download_dir, extension_arg)

    # Create a temporary user data directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        options.add_argument(f'--user-data-dir={tmp_dir}')

        # Initialise the WebDriver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Open the URL
        driver.get("https://myeclerk.myorangeclerk.com/Cases/search")

        # Wait for the form to be loaded
        wait = WebDriverWait(driver, 10)

        # Check for CAPTCHA and wait for it to be solved
        try:
            wait_for_captcha_to_be_solved(driver)
        except Exception as e:
            print(f"Error: {e}")
            driver.quit()
            exit()

        # Ensure we are in the default content
        driver.switch_to.default_content()

        # Re-locate and interact with the elements after CAPTCHA is solved
        try:
            print("Locating case type dropdown")
            case_type_dropdown = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".multiselect"))
            )
            case_type_dropdown.click()
            print("Clicked case type dropdown")

            input_case_types = wait.until(EC.element_to_be_clickable((By.ID, "input-caseTypes")))
            time.sleep(0.5)
            input_case_types.click()
            time.sleep(0.5)
            input_case_types.send_keys("Foreclosure")
            time.sleep(0.5)

            foreclosure_option = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//label[contains(text(), 'Foreclosure')]/input")
                )
            )
            time.sleep(1)
            foreclosure_option.click()
            print("Selected Foreclosure option")

            # Calculate dates
            # for testing purposes, we will set today equal to 9 July 2024

            date_from, date_to = determine_dates(args.date_from, args.date_to)
            
            # Enter Date From
            date_from_input = wait.until(EC.element_to_be_clickable((By.ID, "DateFrom")))
            date_from_input.clear()
            date_from_input.send_keys(date_from)
            print("Entered date from")

            # Enter Date To
            date_to_input = wait.until(EC.element_to_be_clickable((By.ID, "DateTo")))
            date_to_input.clear()
            date_to_input.send_keys(date_to)
            print("Entered date to")

            # Re-locate the search button and click it
            search_button = wait.until(EC.element_to_be_clickable((By.ID, "caseSearch")))
            time.sleep(2)
            search_button.click()
            print("Clicked search button")

            # Wait for the results page to load
            time.sleep(3)

            # After the search results load, add the following code to navigate to the desired start page
            desired_start_page = 1 # Set this to the page number from which you want to start
            current_page = 1  # Initialize the current page counter

            # Ensure the page_number starts from the desired_start_page
            # Ensure the page_number starts from the desired_start_page
            page_number = desired_start_page
            navigate_to_page(page_number)  # Navigate to the starting page before beginning the loop

            # Process links page by page
            while True:
                print(f"Processing page {page_number}")

                # Extract links from the current page
                case_numbers_on_page = extract_links_from_page()

                # Track processed cases for the current page
                page_processed_cases = []

                # Process each link on the current page
                while case_numbers_on_page:
                    case_number = case_numbers_on_page.pop(0)

                    # Skip already processed cases
                    if case_number in processed_cases:
                        continue

                    # Before clicking link, save the text of the link as case number
                    time.sleep(0.5)

                    print(f"Processing case {case_number}")

                    try:
                        # Find the link element again to avoid stale element reference
                        link_element = driver.find_element(By.LINK_TEXT, case_number)
                        link_element.click()

                        time.sleep(1)

                        # Example of calling the function in the main processing loop
                        subfolder_path = create_case_directory(case_number, download_dir)

                        extract_case_title(driver, subfolder_path, case_number)

                        print('about to call extract_and_save_case_details with these params:', driver, subfolder_path, case_number)
                        extract_and_save_case_details(
                            driver, subfolder_path, case_number
                        )

                        # save case initiated date
                        extract_and_save_case_initiated_date(driver, subfolder_path)

                        # Proceed with document downloads
                        process_document_link(driver, case_number, download_dir, 'Complaint', 'Complaint_PDF', subfolder_path)
                        process_document_link(driver, case_number, download_dir, 'Pendens', 'Lis_Pendens_PDF', subfolder_path)
                        process_document_link(driver, case_number, download_dir, 'Value', 'Real_Property_Value_PDF', subfolder_path)

                        # Mark this case as processed
                        processed_cases.append(case_number)

                        # Go back to the case list page
                        driver.back()
                        time.sleep(2)

                        # Re-navigate to the current page to maintain correct position
                        navigate_to_page(page_number)

                        # Re-fetch the list of case numbers on the page to account for dynamic changes
                        case_numbers_on_page = extract_links_from_page()

                    except NoSuchElementException:
                        log_error(case_number, "Case link not found")
                        print(f"Case link not found for {case_number}")
                    except Exception as e:
                        print(f"Error during form interaction: {e}")
                        log_error(case_number, "unknown error (probably missing doc)")
                        # Ensure to close any extra tabs before retrying
                        while len(driver.window_handles) > 1:
                            driver.switch_to.window(driver.window_handles[-1])
                            driver.close()
                        driver.switch_to.window(driver.window_handles[0])

                # After processing all cases on the current page, check if the "Next" button is present
                if is_next_button_present(driver):
                    next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Next')]")
                    next_button.click()

                    page_number += 1

                    # Wait for the new page to load and the case list to be present
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "caseList"))
                    )

                else:
                    print("No more pages to process.")
                    break

        except Exception as e:
            print(f"Error during form interaction: {e}")

    # Keep the browser open for debugging purposes
    driver.quit()
    print("All cases processed successfully.")


if __name__ == '__main__':
    main()
