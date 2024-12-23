import requests
import logging
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin

class TCTMDDownloader:
    def __init__(self, username, password, output_dir="downloads", test_mode=False):
        self.base_url = "https://www.tctmd.com"
        self.api_url = "https://www.tctmd.com/api/v1/search"
        self.login_url = "https://www.tctmd.com/api/v1/user/login"
        self.username = username
        self.password = password
        self.output_dir = output_dir
        self.test_mode = test_mode
        self.session = requests.Session()
        
        # Setup logging
        logging.basicConfig(
            filename='pdf_downloader.log',
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def login(self):
        """
        Login to TCTMD and handle Okta authentication.
        """
        try:
            # Step 1: Login payload
            login_data = {
                "username": self.username,
                "password": self.password,
                "redirect_to": "https://www.tctmd.com/"
            }

            # Step 2: Send POST request to the login endpoint
            response = self.session.post(self.login_url, data=login_data)

            if response.status_code == 200:
                json_data = response.json()

                # Step 3: Check for success and the "cookie_redirect" field
                if json_data.get("success") and "cookie_redirect" in json_data.get("data", {}):
                    cookie_redirect_url = json_data["data"]["cookie_redirect"]

                    # Step 4: Follow the Okta redirect
                    okta_response = self.session.get(cookie_redirect_url)
                    if okta_response.status_code == 200:
                        logging.info("Successfully authenticated via Okta.")
                        return True
                    else:
                        logging.error(f"Okta redirect failed with status code {okta_response.status_code}.")
                else:
                    logging.error("Login response did not contain 'cookie_redirect'.")
            else:
                logging.error(f"Login failed with status code {response.status_code}.")
            return False
        except Exception as e:
            logging.error(f"Error during login: {str(e)}")
            return False

    def get_presentation_urls_from_api(self, page_num):
        """
        Get all presentation URLs directly from the API.
        """
        try:
            params = {
                "keyword": "",
                "type": "slide",
                "subtype": "",
                "subtype_sub_level": "",
                "topic": "",
                "subtopic": "",
                "desc": "true",
                "page": page_num,
                "page_size": 12,
                "year": "",
                "conference": "",
                "sortmode": "Date",
                "matching": "AND",
                "searched": "true"
            }

            # Send GET request to the API
            response = self.session.get(self.api_url, params=params)

            if response.status_code == 200:
                data = response.json()

                # Extract presentation URLs from API response
                items = data.get("data", {}).get("items", [])
                logging.debug(f"API response items: {items}")

                presentations = []
                for item in items:
                    url = item.get("url")  # Use 'url' field instead of 'location'
                    if url:  # Only process if 'url' is not None
                        presentations.append(url)
                        logging.info(f"Valid presentation URL: {url}")
                    else:
                        logging.warning(f"Item has no valid URL: {item}")

                logging.info(f"Found {len(presentations)} presentations on page {page_num}.")
                return presentations

            else:
                logging.error(f"API request failed with status code {response.status_code}.")
                return []

        except Exception as e:
            logging.error(f"Error getting presentation URLs from API: {str(e)}")
            return []

    def get_pdf_url_from_presentation(self, presentation_url):
        """
        Get PDF download URL from a presentation detail page
        """
        try:
            response = self.session.get(presentation_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for PDF download link
                pdf_link = soup.find('a', attrs={'href': lambda x: x and x.endswith('.pdf')})
                if pdf_link and pdf_link.get('href'):
                    pdf_url = pdf_link['href']
                    logging.info(f"Found PDF link: {pdf_url}")
                    return pdf_url

                logging.warning(f"No PDF link found in presentation: {presentation_url}")
            return None
        except Exception as e:
            logging.error(f"Error getting PDF URL from presentation {presentation_url}: {str(e)}")
            return None

    def download_pdf(self, url):
        """
        Download a single PDF
        """
        try:
            filename = os.path.join(self.output_dir, url.split('/')[-1])

            # Skip if already downloaded
            if os.path.exists(filename):
                logging.info(f"PDF already exists: {filename}")
                return True

            response = self.session.get(url, stream=True)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                logging.info(f"Successfully downloaded: {filename}")
                return True
            else:
                logging.error(f"Failed to download {url}: Status code {response.status_code}")
                return False

        except Exception as e:
            logging.error(f"Error in download_pdf: {str(e)}")
            return False

    def download_all_pdfs(self):
        """
        Download all PDFs from search results
        """
        try:
            if not self.login():
                logging.error("Failed to login. Exiting.")
                return False

            logging.info("Successfully logged in, searching for presentations...")

            page_num = 1
            total_downloads = 0

            while True:
                presentations = self.get_presentation_urls_from_api(page_num)

                if not presentations:
                    logging.info("No more presentations found.")
                    break

                for presentation_url in presentations:
                    logging.info(f"Processing presentation: {presentation_url}")
                    pdf_url = self.get_pdf_url_from_presentation(presentation_url)

                    if pdf_url:
                        if self.download_pdf(pdf_url):
                            total_downloads += 1
                            logging.info(f"Successfully downloaded {total_downloads} PDFs.")

                            # Stop if in test mode and downloaded 2 PDFs
                            if self.test_mode and total_downloads >= 2:
                                logging.info("Test mode enabled. Stopping after 2 PDFs.")
                                return True
                    else:
                        logging.warning(f"Could not get PDF URL from {presentation_url}")

                page_num += 1  # Move to the next page

            logging.info(f"Finished downloading {total_downloads} PDFs")
            return True

        except Exception as e:
            logging.error(f"Error in download_all_pdfs: {str(e)}")
            logging.debug("Full error traceback:", exc_info=True)
            return False

if __name__ == "__main__":
    # Replace with your credentials
    USERNAME = "your_email@example.com"
    PASSWORD = "your_password"

    # Set test_mode=True to only download 2 PDFs
    downloader = TCTMDDownloader(USERNAME, PASSWORD, test_mode=True)
    downloader.download_all_pdfs()