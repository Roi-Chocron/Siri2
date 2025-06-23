# Handles opening websites, information searches, form filling, and other web automation

import webbrowser
import requests
from bs4 import BeautifulSoup
# from selenium import webdriver # Placeholder for Selenium
# from selenium.webdriver.common.by import By # Placeholder
# from selenium.webdriver.support.ui import WebDriverWait # Placeholder
# from selenium.webdriver.support import expected_conditions as EC # Placeholder
from jarvis_assistant.core.security_manager import SecurityManager # For secure details
from jarvis_assistant.utils.logger import get_logger # Import logger
from jarvis_assistant.core.command_parser import CommandParser # For LLM-based summarization

# Ensure get_logger can be found if this module is run standalone for testing
if __name__ == '__main__' and __package__ is None:
    import sys
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from jarvis_assistant.utils.logger import get_logger
    # Need CommandParser for standalone summarization test
    from jarvis_assistant.core.command_parser import CommandParser


class WebAutomator:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.default_search_engine = "https://www.google.com/search?q=" # Can be made configurable
        # self.driver = None # For Selenium, initialize when needed
        self.security_manager = SecurityManager()
        # Initialize CommandParser if needed for summarization, or pass it in.
        # For now, let's assume CommandParser might be instantiated if summarization is complex.
        # Or, we can make a simpler LLM call directly.
        # Let's try a direct call to Gemini model for summarization within this class for now.
        # This avoids making WebAutomator dependent on passing CommandParser instance.
        try:
            from jarvis_assistant.config import GEMINI_API_KEY
            import google.generativeai as genai
            if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY":
                genai.configure(api_key=GEMINI_API_KEY)
                self.summarizer_model = genai.GenerativeModel('models/gemini-1.5-flash') # Or a different one if needed
                self.logger.info("Gemini model for summarization initialized in WebAutomator.")
            else:
                self.summarizer_model = None
                self.logger.warning("Gemini API key not configured. LLM-based summarization will be disabled.")
        except Exception as e:
            self.summarizer_model = None
            self.logger.error(f"Failed to initialize Gemini model for summarization in WebAutomator: {e}")


    def open_website(self, url: str) -> bool:
        """Opens a specific website in the default web browser."""
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            webbrowser.open_new_tab(url)
            self.logger.info(f"Opened website: {url}")
            return True
        except Exception as e:
            self.logger.error(f"Error opening website {url}: {e}")
            return False

    def _extract_text_from_html(self, html_content: str) -> str:
        """Extracts meaningful text from HTML content using BeautifulSoup."""
        soup = BeautifulSoup(html_content, 'lxml')

        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        # Get text, attempting to preserve some structure with line breaks for paragraphs/divs
        # This is a heuristic and might need refinement.
        text_parts = []
        for element in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'article', 'section']):
            text = element.get_text(separator=' ', strip=True)
            if text:
                text_parts.append(text)

        full_text = "\n".join(text_parts)
        if not full_text: # Fallback if no specific tags yielded text
            full_text = soup.get_text(separator='\n', strip=True)

        # Reduce multiple newlines to a single one for cleaner output to LLM
        return '\n'.join(line for line in full_text.splitlines() if line.strip())


    def _summarize_text_with_llm(self, text: str, query_context: str = None) -> str | None:
        """Summarizes the given text using the configured LLM."""
        if not self.summarizer_model:
            self.logger.warning("Summarizer model not available. Cannot summarize text with LLM.")
            return None
        if not text or not text.strip():
            self.logger.warning("No text provided to summarize.")
            return "No content found to summarize."

        # Truncate text if it's too long for the LLM context window (e.g., > 20000 chars as a rough limit)
        # Gemini 1.5 Flash has a large context window, but still good practice.
        max_chars = 25000
        if len(text) > max_chars:
            self.logger.info(f"Text too long ({len(text)} chars), truncating to {max_chars} for summarization.")
            text = text[:max_chars]

        prompt = f"Please provide a concise summary of the following text. Focus on the key information."
        if query_context:
            prompt += f"\nThe original query or topic of interest was: '{query_context}'."
        prompt += f"\n\nText to summarize:\n{text}"

        try:
            response = self.summarizer_model.generate_content(prompt)
            summary = response.text.strip()
            self.logger.info(f"LLM summary generated for query '{query_context if query_context else 'N/A'}'. Length: {len(summary)}")
            return summary
        except Exception as e:
            self.logger.error(f"Error during LLM summarization: {e}")
            return "Sorry, I encountered an error while trying to summarize the content."


    def search_info(self, query: str, summarize: bool = False) -> str | None:
        """
        Performs an information search on the default search engine.
        If summarize is True, it fetches the content of the first search result (heuristic)
        and uses an LLM to summarize it.
        Returns the direct search URL (if not summarizing) or summarized text/error message.
        """
        try:
            search_url = self.default_search_engine + query.replace(" ", "+")
            self.logger.info(f"Performing search for: '{query}' at URL: {search_url}")

            if not summarize:
                webbrowser.open_new_tab(search_url)
                self.logger.info(f"Search results for '{query}' opened in browser.")
                return search_url # Return the search URL itself
            else:
                self.logger.info(f"Attempting to fetch and summarize results for '{query}'...")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.google.com/'
                }
                # First, get the search results page
                response = requests.get(search_url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'lxml')

                # Heuristically find the first organic search result link.
                # This is highly dependent on Google's (or other engine's) HTML structure and can break.
                # Google often uses <h3> tags within <a> tags with class 'yuRUbf' or similar for organic results.
                # Or look for <a> tags with an href starting with /url?q= which is a common Google redirect.
                first_result_link = None

                # Try a few common Google selectors
                # Selector 1: Standard organic results
                link_tag = soup.find('div', class_='yuRUbf')
                if link_tag:
                    link_tag = link_tag.find('a')
                    if link_tag and link_tag.get('href'):
                        first_result_link = link_tag.get('href')
                        self.logger.info(f"Found potential first result link (selector 1): {first_result_link}")

                # Selector 2: If above fails, look for simpler <a> inside <h3> (less specific)
                if not first_result_link:
                    for h3 in soup.find_all('h3'):
                        parent_a = h3.find_parent('a')
                        if parent_a and parent_a.get('href') and parent_a.get('href').startswith(('http://', 'https://')):
                            first_result_link = parent_a.get('href')
                            self.logger.info(f"Found potential first result link (selector 2 - h3>a): {first_result_link}")
                            break

                # Selector 3: Google's redirect links (less ideal as they are redirects)
                if not first_result_link:
                    redirect_link = soup.find('a', href=lambda href: href and href.startswith("/url?q="))
                    if redirect_link:
                        full_url = redirect_link.get('href')
                        if full_url.startswith("/url?q="):
                            from urllib.parse import parse_qs, urlparse
                            parsed_url = urlparse(full_url)
                            query_params = parse_qs(parsed_url.query)
                            if 'url' in query_params: # Google Scholar sometimes uses 'url'
                                first_result_link = query_params['url'][0]
                            elif 'q' in query_params: # Standard Google search redirect
                                first_result_link = query_params['q'][0]
                            self.logger.info(f"Found potential first result link (selector 3 - redirect): {first_result_link}")


                if first_result_link:
                    self.logger.info(f"Fetching content from first result: {first_result_link}")
                    page_response = requests.get(first_result_link, headers=headers, timeout=15)
                    page_response.raise_for_status()

                    page_content_html = page_response.text
                    extracted_text = self._extract_text_from_html(page_content_html)

                    if extracted_text:
                        summary = self._summarize_text_with_llm(extracted_text, query_context=query)
                        if summary:
                            return summary
                        else: # LLM summarization failed or disabled
                            webbrowser.open_new_tab(first_result_link) # Open the page directly
                            return f"Could not summarize the content from {first_result_link}. The page has been opened in your browser."
                    else:
                        webbrowser.open_new_tab(first_result_link)
                        return f"Could not extract text from the first search result ({first_result_link}). The page has been opened."
                else:
                    # Fallback if no link found on search page - just open search_url
                    webbrowser.open_new_tab(search_url)
                    return f"Could not identify the first search result link to summarize. Search results for '{query}' opened in browser: {search_url}"

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error during web search request for '{query}': {e}")
            return f"Failed to perform search for '{query}' due to a network or connection error."
        except Exception as e:
            self.logger.error(f"Unexpected error searching info for '{query}': {e}", exc_info=True)
            # Fallback to just opening the search page if summarization fails badly
            search_url_fallback = self.default_search_engine + query.replace(" ", "+")
            webbrowser.open_new_tab(search_url_fallback)
            return f"An unexpected error occurred while trying to search and summarize. Opened search results for '{query}' in browser: {search_url_fallback}"


    def _initialize_selenium_driver(self):
        """Initializes Selenium WebDriver if not already done."""
        # if self.driver is None:
        #     try:
        #         # This requires ChromeDriver (or other browser driver) to be in PATH
        #         # or specify executable_path
        #         # from selenium.webdriver.chrome.service import Service as ChromeService
        #         # from webdriver_manager.chrome import ChromeDriverManager
        #         # self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
        #
        #         # Simpler setup if chromedriver is in PATH:
        #         # self.driver = webdriver.Chrome()
        #         print("Selenium WebDriver initialized (placeholder).")
        #     except Exception as e:
        #         print(f"Failed to initialize Selenium WebDriver: {e}")
        #         print("Please ensure you have the correct WebDriver installed and in your PATH.")
        #         self.driver = None # Ensure it's None if initialization fails
        print("Selenium WebDriver initialization is currently a placeholder.")


    def fill_registration_form(self, url: str, user_details_keys: dict, username_for_secrets: str) -> bool:
        """
        Fills a registration form on a given URL using Selenium.
        user_details_keys maps form field names/IDs/xpaths to keys in SecurityManager.
        Example: {'name_field_id': 'full_name', 'email_field_id': 'email_address'}
        """
        self._initialize_selenium_driver()
        # if not self.driver:
        #     print("Selenium driver not available. Cannot fill form.")
        #     return False
        print(f"Placeholder: Navigating to {url} with Selenium (not actually running).")
        print("Placeholder: Attempting to fill form using details from SecurityManager.")

        # try:
        #     self.driver.get(url)
        #     # Example: wait for a known element to ensure page is loaded
        #     # WebDriverWait(self.driver, 10).until(
        #     #     EC.presence_of_element_located((By.ID, "some_form_element_id"))
        #     # )

        #     for field_locator, data_key in user_details_keys.items():
        #         value_to_fill = self.security_manager.get_sensitive_data(username_for_secrets, data_key)
        #         if value_to_fill:
        #             try:
        #                 # This assumes field_locator is an ID. Adapt for name, xpath, etc.
        #                 element = self.driver.find_element(By.ID, field_locator)
        #                 # Or By.NAME, By.XPATH, etc.
        #                 element.send_keys(value_to_fill)
        #                 print(f"Filled field '{field_locator}' with data from '{data_key}'.")
        #             except Exception as e_field:
        #                 print(f"Could not find or fill field '{field_locator}': {e_field}")
        #         else:
        #             print(f"No data found for '{data_key}' in secure storage.")

        #     # Placeholder: Potentially click a submit button
        #     # submit_button = self.driver.find_element(By.ID, "submit_button_id")
        #     # submit_button.click()
        #     print("Form filling attempt complete (placeholder).")
        #     return True # Placeholder
        # except Exception as e:
        #     print(f"Error during form filling with Selenium: {e}")
        #     return False
        # finally:
        #     # Decide if you want to close the browser after each form fill
        #     # if self.driver:
        #     #     self.driver.quit()
        #     #     self.driver = None
        #     pass
        return True # Placeholder for success

    def perform_online_purchase(self, purchase_details: dict, username_for_secrets: str) -> bool:
        """
        Placeholder for performing an online purchase.
        This is EXTREMELY SENSITIVE and requires robust security and error handling.
        'purchase_details' would contain item URL, quantity, etc.
        Payment and shipping info would be fetched via SecurityManager.
        """
        print("\n--- ONLINE PURCHASE SIMULATION ---")
        if not self.security_manager.authenticate_user_for_transaction(): # CRITICAL STEP
            print("Online purchase cancelled due to failed authentication.")
            return False

        self._initialize_selenium_driver()
        # if not self.driver:
        #     print("Selenium driver not available. Cannot perform purchase.")
        #     return False

        print(f"Simulating purchase for item: {purchase_details.get('item_url', 'Unknown item')}")

        # 1. Navigate to item page (Placeholder)
        # self.driver.get(purchase_details.get('item_url'))

        # 2. Add to cart (Placeholder - highly site-specific)
        # add_to_cart_button = self.driver.find_element(By.ID, "add-to-cart-button-id") # Example
        # add_to_cart_button.click()
        print("Simulated: Added item to cart.")

        # 3. Navigate to checkout (Placeholder)
        # checkout_button = self.driver.find_element(By.ID, "checkout-button-id") # Example
        # checkout_button.click()
        print("Simulated: Navigated to checkout.")

        # 4. Fill shipping information (Placeholder)
        # shipping_address = self.security_manager.get_sensitive_data(username_for_secrets, "shipping_address_full")
        # if shipping_address:
        #     # Fill form fields using Selenium
        #     print(f"Simulated: Filled shipping address: {shipping_address[:30]}...")
        # else:
        #     print("Shipping address not found in secure storage. Purchase cannot proceed.")
        #     return False
        print("Simulated: Filled shipping information using stored details.")

        # 5. Fill payment information (Placeholder - EXTREMELY SENSITIVE)
        # payment_cc_number = self.security_manager.get_sensitive_data(username_for_secrets, "credit_card_number")
        # payment_cc_expiry = self.security_manager.get_sensitive_data(username_for_secrets, "credit_card_expiry")
        # payment_cc_cvv = self.security_manager.get_sensitive_data(username_for_secrets, "credit_card_cvv")
        # if payment_cc_number and payment_cc_expiry and payment_cc_cvv:
        #     # Fill payment form fields using Selenium
        #     print("Simulated: Filled payment information using stored details.")
        # else:
        #     print("Payment information not complete in secure storage. Purchase cannot proceed.")
        #     return False
        print("Simulated: Filled payment information using stored details.")

        # 6. Confirm purchase (Placeholder)
        # confirm_purchase_button = self.driver.find_element(By.ID, "confirm-purchase-button-id")
        # confirm_purchase_button.click() # This is the point of no return in a real scenario
        print("Simulated: Confirmed purchase.")
        print("--- ONLINE PURCHASE SIMULATION COMPLETE ---")
        return True # Placeholder

    def close_selenium_driver(self):
        # if self.driver:
        #     try:
        #         self.driver.quit()
        #         print("Selenium WebDriver closed.")
        #     except Exception as e:
        #         print(f"Error closing Selenium WebDriver: {e}")
        #     finally:
        #         self.driver = None
        print("Selenium WebDriver close is currently a placeholder.")


if __name__ == '__main__':
    web_automator = WebAutomator()
    test_user = "jarvis_web_test" # For security manager

    # Test opening website
    web_automator.open_website("google.com")
    web_automator.open_website("https://www.wikipedia.org")

    # Test information search
    print("\n--- Search Test (No Summary) ---")
    web_automator.search_info("latest AI research trends")

    print("\n--- Search Test (With Summary Attempt) ---")
    summary = web_automator.search_info("What is the capital of France?", summarize=True)
    if summary: print(f"Search Result/Summary:\n{summary}")

    # Setup for form filling and purchase (storing dummy data)
    # In a real scenario, the user would have already stored this securely
    sm = SecurityManager()
    sm.store_sensitive_data(test_user, "form_email", "testuser@example-automation.com")
    sm.store_sensitive_data(test_user, "form_name", "Test User Automation")
    # IMPORTANT: Real financial details should NEVER be hardcoded or handled insecurely.
    # The following are for placeholder demonstration of the purchase flow ONLY.
    sm.store_sensitive_data(test_user, "shipping_address_full", "123 Automation Lane, Testville, CA 90210")
    sm.store_sensitive_data(test_user, "credit_card_number", "0000111122223333") # DUMMY
    sm.store_sensitive_data(test_user, "credit_card_expiry", "12/25") # DUMMY
    sm.store_sensitive_data(test_user, "credit_card_cvv", "123") # DUMMY


    # Test form filling (Placeholder - requires a live form and Selenium setup)
    # print("\n--- Form Filling Test (Placeholder) ---")
    # A publicly available safe test form: https://www.selenium.dev/selenium/web/web-form.html
    # registration_details = {
    #     "my-text-id": "form_name",  # Assuming 'my-text-id' is the ID of a name field
    #     "my-email-id": "form_email" # Assuming 'my-email-id' is the ID of an email field
    # }
    # web_automator.fill_registration_form("https://www.selenium.dev/selenium/web/web-form.html", registration_details, test_user)

    # Test online purchase (Placeholder - EXTREMELY SENSITIVE, SIMULATION ONLY)
    # print("\n--- Online Purchase Test (Placeholder Simulation) ---")
    # purchase_data = {
    #     "item_url": "https://www.example.com/test_product_page_for_automation" # Replace with a safe, non-transactional page
    # }
    # web_automator.perform_online_purchase(purchase_data, test_user)

    # Clean up Selenium driver if it was used
    web_automator.close_selenium_driver()

    # Clean up dummy security data
    print("\nCleaning up dummy security data...")
    sm.delete_sensitive_data(test_user, "form_email")
    sm.delete_sensitive_data(test_user, "form_name")
    sm.delete_sensitive_data(test_user, "shipping_address_full")
    sm.delete_sensitive_data(test_user, "credit_card_number")
    sm.delete_sensitive_data(test_user, "credit_card_expiry")
    sm.delete_sensitive_data(test_user, "credit_card_cvv")
    print("Cleanup complete.")
