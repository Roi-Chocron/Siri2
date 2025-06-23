# Handles authentication, secure storage

import keyring
import getpass # For securely getting master password if needed

class SecurityManager:
    SERVICE_NAME = "JARVIS_ASSISTANT"

    def store_sensitive_data(self, username: str, data_key: str, data_value: str):
        """
        Stores sensitive data securely in the system's keyring.
        The 'username' here could be a generic user for the assistant or specific if multi-user.
        'data_key' is what the data is for, e.g., 'google_form_email'.
        """
        try:
            keyring.set_password(self.SERVICE_NAME, f"{username}_{data_key}", data_value)
            print(f"Data for '{data_key}' stored securely.")
        except Exception as e:
            print(f"Error storing sensitive data: {e}")

    def get_sensitive_data(self, username: str, data_key: str) -> str | None:
        """
        Retrieves sensitive data from the system's keyring.
        Returns None if not found or if an error occurs.
        """
        try:
            data = keyring.get_password(self.SERVICE_NAME, f"{username}_{data_key}")
            if data:
                print(f"Data for '{data_key}' retrieved.")
                return data
            else:
                print(f"No data found for '{data_key}'.")
                return None
        except Exception as e:
            print(f"Error retrieving sensitive data: {e}")
            return None

    def delete_sensitive_data(self, username: str, data_key: str):
        """
        Deletes sensitive data from the system's keyring.
        """
        try:
            keyring.delete_password(self.SERVICE_NAME, f"{username}_{data_key}")
            print(f"Data for '{data_key}' deleted.")
        except keyring.errors.PasswordDeleteError:
            print(f"No data found for '{data_key}' to delete or deletion failed.")
        except Exception as e:
            print(f"Error deleting sensitive data: {e}")

    def authenticate_user_for_transaction(self) -> bool:
        """
        Placeholder for a robust user authentication before financial transactions.
        This needs to be significantly more advanced for real-world use.
        For now, it might ask for a master password or use OS-level authentication.
        """
        # IMPORTANT: This is a very basic placeholder.
        # Real authentication should involve multi-factor authentication (MFA)
        # and potentially integrate with OS biometric features if possible.
        print("CRITICAL ACTION: User authentication required for financial transaction.")
        try:
            # This is NOT secure enough for real financial transactions.
            # It's just a demonstration placeholder.
            password = getpass.getpass("Enter your master password to authorize this transaction: ")
            # In a real scenario, you'd compare this against a securely hashed and salted password.
            # For this example, let's assume a hardcoded password for testing (VERY INSECURE).
            # Replace 'SUPER_SECRET_PASSWORD' with a more secure mechanism in any real deployment.
            # Or, better yet, integrate with OS authentication.
            if password == "SUPER_SECRET_PASSWORD_DEMO_ONLY": # Replace or remove this
                print("Authentication successful (DEMO).")
                return True
            else:
                print("Authentication failed.")
                return False
        except Exception as e:
            print(f"Error during authentication: {e}")
            return False


if __name__ == '__main__':
    manager = SecurityManager()
    test_user = "test_user_jarvis"

    # Test storing data
    manager.store_sensitive_data(test_user, "test_api_key", "12345abcdef")
    manager.store_sensitive_data(test_user, "email_address", "test@example.com")

    # Test retrieving data
    api_key = manager.get_sensitive_data(test_user, "test_api_key")
    if api_key:
        print(f"Retrieved API Key: {api_key}")

    email = manager.get_sensitive_data(test_user, "email_address")
    if email:
        print(f"Retrieved Email: {email}")

    non_existent = manager.get_sensitive_data(test_user, "non_existent_key")

    # Test deleting data
    manager.delete_sensitive_data(test_user, "test_api_key")
    api_key_after_delete = manager.get_sensitive_data(test_user, "test_api_key")
    if not api_key_after_delete:
        print("API key successfully deleted or was not found after deletion attempt.")

    # Test transaction authentication
    print("\nAttempting transaction authentication...")
    if manager.authenticate_user_for_transaction():
        print("Transaction would proceed.")
    else:
        print("Transaction would be cancelled.")

    # Clean up remaining test data
    manager.delete_sensitive_data(test_user, "email_address")
