import requests
import logging
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urljoin


class TCTMDDownloader:
    def __init__(self, username, password, output_dir="downloads", test_mode=False):
        self.base_url = "https://www.tctmd.com"
        self.search_url = "https://www.tctmd.com/search"
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
            
        # Create a file to track downloaded PDFs
        self.downloaded_file = "downloaded_pdfs.txt"
        if not os.path.exists(self.downloaded_file):
            with open(self.downloaded_file, "w") as f:
                pass

    def verify_login(self):
        """Verify if login was successful by checking for user-logged-in class"""
        try:
            # Add a small delay to let the session establish
            time.sleep(2)
            
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for the logged-in class in body tag
                body = soup.find('body')
                if body and 'user-logged-in' in body.get('class', []):
                    logging.info("Login verified - found user-logged-in class")
                    return True
                
                # If not found, check the raw text for the class
                if 'user-logged-in' in response.text:
                    logging.info("Login verified - found user-logged-in in page source")
                    return True
                
                logging.debug("Could not find user-logged-in class")
                logging.debug(f"Body classes found: {body.get('class', []) if body else 'No body tag found'}")
                return False
            
            logging.error(f"Failed to get page for verification, status code: {response.status_code}")
            return False
            
        except Exception as e:
            logging.error(f"Error verifying login: {str(e)}")
            logging.debug("Full error traceback:", exc_info=True)
            return False

    def follow_okta_redirect(self, redirect_url):
        """Handle Okta redirect chain properly"""
        try:
            logging.debug(f"Following Okta redirect: {redirect_url}")
            
            # Headers exactly matching what we see in the browser
            okta_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache, no-store',
                'Connection': 'keep-alive',
                'Host': 'tctmd.okta.com',
                'Pragma': 'no-cache',
                'Referer': 'https://www.tctmd.com/',
                'Sec-Ch-Ua': '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A_Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
            }
            
            # Follow redirect chain manually
            max_redirects = 5
            current_url = redirect_url
            
            for i in range(max_redirects):
                logging.debug(f"Request {i+1}: {current_url}")
                
                # Update host header based on URL
                if 'tctmd.okta.com' in current_url:
                    okta_headers['Host'] = 'tctmd.okta.com'
                elif 'www.tctmd.com' in current_url:
                    okta_headers['Host'] = 'www.tctmd.com'
                
                response = self.session.get(
                    current_url,
                    headers=okta_headers,
                    allow_redirects=False
                )
                
                logging.debug(f"Status: {response.status_code}")
                logging.debug(f"Headers: {dict(response.headers)}")
                
                # Process cookies from response
                if 'set-cookie' in response.headers:
                    logging.debug("Cookies being set")
                    cookies_str = response.headers['set-cookie']
                    for cookie in cookies_str.split(', '):
                        logging.debug(f"Cookie: {cookie}")
                
                if response.status_code in (301, 302, 303, 307):
                    current_url = response.headers.get('location')
                    if not current_url:
                        logging.error("Redirect with no Location header")
                        return False
                    
                    # If we're redirecting to TCTMD, update headers
                    if 'www.tctmd.com' in current_url:
                        logging.debug("Switching to TCTMD domain")
                        okta_headers['Host'] = 'www.tctmd.com'
                        okta_headers['Origin'] = 'https://www.tctmd.com'
                        okta_headers['Referer'] = 'https://tctmd.okta.com/'
                    
                    logging.debug(f"Following redirect to: {current_url}")
                    continue
                    
                elif response.status_code == 200:
                    return self.verify_login()
                else:
                    logging.error(f"Unexpected status code: {response.status_code}")
                    return False
            
            logging.error("Too many redirects")
            return False
            
        except Exception as e:
            logging.error(f"Error during Okta redirect: {str(e)}")
            logging.debug("Full error traceback:", exc_info=True)
            return False

    def login(self):
        """Login to TCTMD website using their API endpoint and handle Okta authentication"""
        try:
            # First get the main page to get initial cookies and clear any existing session
            self.session.cookies.clear()
            initial_response = self.session.get(self.base_url)
            
            # Set up headers for initial login
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': 'https://www.tctmd.com',
                'Referer': 'https://www.tctmd.com/',
                'X-Requested-With': 'XMLHttpRequest',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0'
            }
            
            # Initial login request
            login_data = {
                'username': self.username,
                'password': self.password,
                'redirect_to': 'https://www.tctmd.com/'
            }
            
            # Submit login request
            response = self.session.post(
                self.login_url,
                data=login_data,
                headers=headers
            )
            
            logging.info(f"Initial login response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get('success'):
                        cookie_redirect = response_data.get('data', {}).get('cookie_redirect')
                        if cookie_redirect:
                            return self.follow_okta_redirect(cookie_redirect)
                            
                except Exception as e:
                    logging.error(f"Error during login process: {str(e)}")
                    logging.error(f"Response content: {response.text[:500]}")
                    return False
            
            logging.error("Login failed - unexpected response")
            logging.error(f"Response content: {response.text[:500]}")
            return False
                
        except Exception as e:
            logging.error(f"Login error: {str(e)}")
            logging.debug("Full error traceback:", exc_info=True)
            return False

    def get_presentation_urls_from_page(self, page_num):
        """Get all presentation URLs from a search results page"""
        try:
            search_params = {
                'keyword': '',
                'type': 'slide',
                'desc': 'true',
                'page': page_num,
                'page_size': 12,
                'sortmode': 'Date',
                'matching': 'AND',
                'searched': 'true'
            }
            
            response = self.session.get(f"{self.base_url}/search", params=search_params)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find the content block
                content_block = soup.find('div', id='block-tctmd-content')
                if not content_block:
                    logging.error("Could not find main content block")
                    return []
                
                # Find all slide result divs
                slide_divs = content_block.find_all('div', class_='search-page__results')
                if not slide_divs:
                    logging.error("No slide results found")
                    logging.debug("Content block HTML:")
                    logging.debug(content_block.prettify()[:1000])
                    return []
                
                presentations = []
                for div in slide_divs:
                    # Find the main link in each slide div
                    link = div.find('a', href=True)
                    if link and '/slide/' in link['href']:
                        full_url = urljoin(self.base_url, link['href'])
                        if full_url not in presentations:  # Avoid duplicates
                            presentations.append(full_url)
                            logging.info(f"Found presentation: {full_url}")
                
                if not presentations:
                    logging.warning("Found slide divs but no valid presentation links")
                    logging.debug("First slide div content:")
                    if slide_divs:
                        logging.debug(slide_divs[0].prettify())
                
                return presentations
            
            logging.error(f"Failed to get search page: {response.status_code}")
            return []
            
        except Exception as e:
            logging.error(f"Error getting presentations from page {page_num}: {str(e)}")
            logging.debug("Full error traceback:", exc_info=True)
            return []

    def get_pdf_url_from_presentation(self, presentation_url):
        """Get PDF download URL from a presentation detail page"""
        try:
            response = self.session.get(presentation_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Log the first part of the HTML for debugging
                logging.debug(f"Presentation page HTML: {response.text[:2000]}")
                
                # Look for PDF download link
                pdf_link = soup.find('a', attrs={'data-feathr-click-track': 'true', 'href': lambda x: x and x.endswith('.pdf')})
                if pdf_link and pdf_link.get('href'):
                    pdf_url = pdf_link['href']
                    logging.info(f"Found PDF link: {pdf_url}")
                    return pdf_url
                
                logging.warning(f"No PDF link found in presentation: {presentation_url}")
            return None
        except Exception as e:
            logging.error(f"Error getting PDF URL from presentation {presentation_url}: {str(e)}")
            return None

    def download_pdf(self, url, retry_count=3):
        """Download a single PDF with retry logic"""
        try:
            filename = os.path.join(self.output_dir, url.split('/')[-1])
            
            # Skip if already downloaded
            if os.path.exists(filename):
                logging.info(f"PDF already exists: {filename}")
                return True
                
            # Check if already in downloaded list
            with open(self.downloaded_file, "r") as f:
                if url in f.read():
                    logging.info(f"PDF already recorded as downloaded: {filename}")
                    return True
            
            for attempt in range(retry_count):
                try:
                    response = self.session.get(url, stream=True)
                    if response.status_code == 200:
                        with open(filename, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        # Record successful download
                        with open(self.downloaded_file, "a") as f:
                            f.write(f"{url}\n")
                        
                        logging.info(f"Successfully downloaded: {filename}")
                        return True
                        
                    elif response.status_code == 403:
                        logging.error(f"Access denied for {url}")
                        return False
                    
                    else:
                        logging.error(f"Failed to download {url}: Status code {response.status_code}")
                        
                except Exception as e:
                    logging.error(f"Error downloading {url}: {str(e)}")
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                    
            return False
            
        except Exception as e:
            logging.error(f"Error in download_pdf: {str(e)}")
            return False

    def download_all_pdfs(self):
        """Download all PDFs from search results"""
        try:
            if not self.login():
                logging.error("Failed to login. Exiting.")
                return False
            
            logging.info("Successfully logged in, searching for presentations...")
            
            # Get first page of presentations for testing
            presentations = self.get_presentation_urls_from_page(1)
            
            if not presentations:
                logging.error("No presentations found on first page")
                return False
            
            logging.info(f"Found {len(presentations)} presentations on first page")
            
            # For testing, just try the first two presentations
            download_count = 0
            for presentation_url in presentations[:2]:
                logging.info(f"Processing presentation: {presentation_url}")
                pdf_url = self.get_pdf_url_from_presentation(presentation_url)
                
                if pdf_url:
                    if self.download_pdf(pdf_url):
                        download_count += 1
                        logging.info(f"Successfully downloaded PDF {download_count}/2 from {presentation_url}")
                        time.sleep(1)  # Small delay between downloads
                else:
                    logging.warning(f"Could not get PDF URL from {presentation_url}")
            
            logging.info(f"Finished downloading {download_count} PDFs")
            return True
            
        except Exception as e:
            logging.error(f"Error in download_all_pdfs: {str(e)}")
            logging.debug("Full error traceback:", exc_info=True)
            return False

if __name__ == "__main__":
    # Replace with your credentials
    USERNAME = "JHart@hartconnltd.com"
    PASSWORD = "Cpticd10cm2!"
    
    # Set test_mode=True to only download 2 PDFs
    downloader = TCTMDDownloader(USERNAME, PASSWORD, test_mode=True)
    downloader.download_all_pdfs()