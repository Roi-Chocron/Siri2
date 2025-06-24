import os
import json
import keyring
from keyring.errors import NoKeyringError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from jarvis_assistant.utils.logger import get_logger

logger = get_logger("GoogleAuthManager")

# Define a service name for keyring
KEYRING_SERVICE_NAME_PREFIX = "jarvis_assistant_google_tokens_" # Suffix will be scope specific
# Define a fallback token file path if keyring is not available
USER_HOME = os.path.expanduser("~")
FALLBACK_TOKEN_DIR = os.path.join(USER_HOME, ".jarvis_assistant")
# FALLBACK_TOKEN_FILE_PREFIX will be similar to KEYRING_SERVICE_NAME_PREFIX

# Default path for client secrets file
DEFAULT_CLIENT_SECRET_FILE = "client_secret.json" # Expected in project root

class GoogleAuthManager:
    def __init__(self, client_secret_file=None, scopes=None):
        """
        Manages Google API authentication and token storage.

        Args:
            client_secret_file (str, optional): Path to the client_secret.json file.
                                                Defaults to 'client_secret.json' in project root.
            scopes (list of str, optional): List of scopes required for the API.
        """
        if client_secret_file is None:
            # Assume client_secret.json is in the parent directory of 'core' (i.e., project root)
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            self.client_secret_file = os.path.join(base_dir, DEFAULT_CLIENT_SECRET_FILE)
        else:
            self.client_secret_file = client_secret_file

        if not os.path.exists(self.client_secret_file):
            logger.error(f"Client secrets file not found at: {self.client_secret_file}")
            logger.error("Please ensure you have downloaded it from Google Cloud Platform and placed it correctly.")
            logger.error(f"Refer to docs/google_api_setup.md for instructions.")
            raise FileNotFoundError(f"Client secrets file not found: {self.client_secret_file}")

        self.scopes = scopes if scopes else []
        self.creds = None

        # Generate a unique identifier for this set of scopes for token storage
        self.scope_id = "_".join(sorted(self.scopes)).replace("/", "_").replace(":", "_")
        self.keyring_username = f"{KEYRING_SERVICE_NAME_PREFIX}{self.scope_id}"
        self.fallback_token_file = os.path.join(FALLBACK_TOKEN_DIR, f"token_{self.scope_id}.json")


    def _save_credentials(self, credentials):
        """Saves credentials securely using keyring or fallback to a local file."""
        creds_json = credentials.to_json()
        try:
            keyring.set_password(self.keyring_username, self.keyring_username, creds_json)
            logger.info(f"Credentials saved to keyring for user '{self.keyring_username}'.")
        except NoKeyringError:
            logger.warning("No keyring backend found. Falling back to local file for token storage.")
            os.makedirs(FALLBACK_TOKEN_DIR, exist_ok=True)
            try:
                with open(self.fallback_token_file, "w") as token_file:
                    token_file.write(creds_json)
                os.chmod(self.fallback_token_file, 0o600) # Set strict permissions
                logger.info(f"Credentials saved to fallback file: {self.fallback_token_file}")
            except IOError as e:
                logger.error(f"Failed to save credentials to fallback file: {e}")
                raise
        except Exception as e: # Catch other potential keyring errors
            logger.error(f"An unexpected error occurred while saving credentials to keyring: {e}")
            logger.warning("Falling back to local file for token storage due to keyring error.")
            os.makedirs(FALLBACK_TOKEN_DIR, exist_ok=True)
            try:
                with open(self.fallback_token_file, "w") as token_file:
                    token_file.write(creds_json)
                os.chmod(self.fallback_token_file, 0o600)
                logger.info(f"Credentials saved to fallback file: {self.fallback_token_file}")
            except IOError as e_io:
                logger.error(f"Failed to save credentials to fallback file after keyring error: {e_io}")
                raise


    def _load_credentials(self):
        """Loads credentials from keyring or fallback local file."""
        creds_json = None
        try:
            creds_json = keyring.get_password(self.keyring_username, self.keyring_username)
            if creds_json:
                logger.info(f"Credentials loaded from keyring for user '{self.keyring_username}'.")
        except NoKeyringError:
            logger.warning("No keyring backend found. Attempting to load from fallback local file.")
            if os.path.exists(self.fallback_token_file):
                try:
                    with open(self.fallback_token_file, "r") as token_file:
                        creds_json = token_file.read()
                    logger.info(f"Credentials loaded from fallback file: {self.fallback_token_file}")
                except IOError as e:
                    logger.error(f"Failed to load credentials from fallback file: {e}")
                    return None
            else:
                logger.info("Fallback token file not found.")
                return None
        except Exception as e: # Catch other potential keyring errors
            logger.error(f"An unexpected error occurred while loading credentials from keyring: {e}")
            logger.warning("Attempting to load from fallback local file due to keyring error.")
            if os.path.exists(self.fallback_token_file):
                try:
                    with open(self.fallback_token_file, "r") as token_file:
                        creds_json = token_file.read()
                    logger.info(f"Credentials loaded from fallback file: {self.fallback_token_file}")
                except IOError as e_io:
                    logger.error(f"Failed to load credentials from fallback file after keyring error: {e_io}")
                    return None
            else:
                logger.info("Fallback token file not found after keyring error.")
                return None

        if creds_json:
            try:
                return Credentials.from_authorized_user_info(json.loads(creds_json), self.scopes)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse credentials JSON: {e}")
                # Potentially delete the corrupted token to allow re-authentication
                self._delete_credentials()
                return None
            except Exception as e: # Catch other errors from Credentials.from_authorized_user_info
                logger.error(f"Failed to load credentials from JSON data: {e}")
                self._delete_credentials()
                return None
        return None

    def _delete_credentials(self):
        """Deletes stored credentials from keyring and fallback file."""
        try:
            keyring.delete_password(self.keyring_username, self.keyring_username)
            logger.info(f"Credentials deleted from keyring for user '{self.keyring_username}'.")
        except NoKeyringError:
            logger.info("No keyring backend found, skipping keyring deletion.")
        except Exception as e:
            logger.error(f"Error deleting credentials from keyring: {e}")

        if os.path.exists(self.fallback_token_file):
            try:
                os.remove(self.fallback_token_file)
                logger.info(f"Fallback token file deleted: {self.fallback_token_file}")
            except OSError as e:
                logger.error(f"Error deleting fallback token file: {e}")


    def get_credentials(self):
        """
        Gets valid Google API credentials.
        Handles loading stored credentials, refreshing them, or running the OAuth flow.
        """
        if self.creds and self.creds.valid:
            return self.creds

        self.creds = self._load_credentials()

        if self.creds and self.creds.expired and self.creds.refresh_token:
            logger.info("Credentials expired, attempting to refresh...")
            try:
                self.creds.refresh(Request())
                self._save_credentials(self.creds) # Save refreshed credentials
                logger.info("Credentials refreshed successfully.")
            except Exception as e: # Broad exception for refresh errors
                logger.error(f"Failed to refresh credentials: {e}")
                logger.warning("User may need to re-authenticate.")
                # If refresh fails, delete the bad credentials so user is prompted to re-auth next time.
                self._delete_credentials()
                self.creds = None # Force re-authentication

        if not self.creds or not self.creds.valid:
            if not self.scopes:
                logger.error("No scopes provided for authentication.")
                raise ValueError("Scopes must be provided to GoogleAuthManager for new authentication.")

            logger.info("No valid credentials found or refresh failed. Starting OAuth flow.")
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secret_file, self.scopes
            )
            # TODO: Consider how to handle port selection for local server if needed,
            # or if a specific port is already in use.
            # For now, let flow.run_local_server() use its default.
            try:
                # Ensure the user is informed about the browser opening
                print("\nJ.A.R.V.I.S. needs to authenticate with Google.")
                print("Your web browser will now open to ask for your permission.")
                print("If it doesn't open automatically, please open the URL printed in the console.")
                self.creds = flow.run_local_server(port=0) # port=0 finds a free port
                self._save_credentials(self.creds)
                logger.info("OAuth flow completed. Credentials obtained and saved.")
            except Exception as e:
                logger.error(f"OAuth flow failed: {e}", exc_info=True)
                # Potentially print a more user-friendly message to console too
                print(f"\nGoogle authentication failed: {e}")
                print("Please ensure you have correctly set up your Google Cloud Project and client_secret.json.")
                return None # Indicate failure

        return self.creds

    def get_authenticated_service(self, service_name, version):
        """
        Returns an authenticated Google API service client.

        Args:
            service_name (str): The name of the service (e.g., 'calendar', 'gmail').
            version (str): The version of the service (e.g., 'v3', 'v1').

        Returns:
            A Google API service object, or None if authentication fails.
        """
        from googleapiclient.discovery import build

        credentials = self.get_credentials()
        if not credentials:
            logger.error(f"Failed to get credentials for {service_name} API.")
            return None
        try:
            service = build(service_name, version, credentials=credentials)
            logger.info(f"Successfully built authenticated service for {service_name} {version}.")
            return service
        except Exception as e:
            logger.error(f"Failed to build Google API service {service_name} {version}: {e}", exc_info=True)
            return None

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # You would need a client_secret.json file from your GCP project.
    # And you'd need to have enabled the Google Calendar API for that project.

    print("Testing GoogleAuthManager...")
    # Ensure client_secret.json is in the project root for this test
    # Adjust path if your PWD is not the project root when running this directly.
    # Assuming PWD is 'jarvis_assistant' when running 'python core/google_auth_manager.py'
    # then client_secret_file should be '../client_secret.json'

    # For direct execution from core/, client_secret.json is one level up from jarvis_assistant/
    # So if jarvis_assistant/ is the project root, and this file is jarvis_assistant/core/google_auth_manager.py
    # then client_secret_file should be os.path.join(os.path.dirname(__file__), '..', '..', 'client_secret.json')
    # However, the class itself defaults to expecting it in the project root (parent of 'core').
    # For this direct test, let's assume it's in the correct location relative to class's default.

    # Test with Calendar scopes
    calendar_scopes = ['https://www.googleapis.com/auth/calendar.readonly']
    print(f"\nAttempting to authenticate with Calendar scopes: {calendar_scopes}")
    try:
        # The default client_secret_file path in the constructor should work if client_secret.json is in jarvis_assistant/
        auth_manager_calendar = GoogleAuthManager(scopes=calendar_scopes)
        calendar_service = auth_manager_calendar.get_authenticated_service('calendar', 'v3')

        if calendar_service:
            print("\nSuccessfully obtained Google Calendar service object.")
            print("Fetching up to 5 upcoming events...")
            import datetime
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            events_result = calendar_service.events().list(
                calendarId='primary', timeMin=now,
                maxResults=5, singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            if not events:
                print("No upcoming events found.")
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(f"{start} - {event['summary']}")
        else:
            print("Failed to obtain Google Calendar service object.")

    except FileNotFoundError as fnf_error:
        print(f"\nTest Error: {fnf_error}")
        print("Make sure 'client_secret.json' is in the 'jarvis_assistant' directory for this test to run.")
    except Exception as e:
        print(f"\nAn error occurred during the Calendar test: {e}")
        logger.error("Test exception", exc_info=True)

    # Test with Gmail scopes (optional, uncomment to test)
    # gmail_scopes = ['https://www.googleapis.com/auth/gmail.readonly']
    # print(f"\nAttempting to authenticate with Gmail scopes: {gmail_scopes}")
    # try:
    #     auth_manager_gmail = GoogleAuthManager(scopes=gmail_scopes)
    #     gmail_service = auth_manager_gmail.get_authenticated_service('gmail', 'v1')
    #     if gmail_service:
    #         print("\nSuccessfully obtained Gmail service object.")
    #         # Example: List labels
    #         results = gmail_service.users().labels().list(userId='me').execute()
    #         labels = results.get('labels', [])
    #         if not labels:
    #             print('No labels found.')
    #         else:
    #             print('Labels:')
    #             for label in labels:
    #                 print(f"- {label['name']}")
    #     else:
    #         print("Failed to obtain Gmail service object.")
    # except FileNotFoundError as fnf_error:
    #     print(f"\nTest Error: {fnf_error}")
    #     print("Make sure 'client_secret.json' is in the 'jarvis_assistant' directory for this test to run.")
    # except Exception as e:
    #     print(f"\nAn error occurred during the Gmail test: {e}")
    #     logger.error("Test exception", exc_info=True)

    print("\nGoogleAuthManager test finished.")
