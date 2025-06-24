# Setting Up Google API Access for J.A.R.V.I.S.

To enable J.A.R.V.I.S. to access Google Calendar and Gmail data, you need to set up a project on the Google Cloud Platform (GCP), enable the necessary APIs, and generate OAuth 2.0 credentials.

Follow these steps carefully:

## 1. Create or Select a Project in Google Cloud Platform

1.  Go to the [Google Cloud Platform Console](https://console.cloud.google.com/).
2.  If you don't have a project, create one:
    *   Click on the project selector dropdown at the top of the page (it might say "Select a project").
    *   Click "NEW PROJECT".
    *   Enter a "Project name" (e.g., "JARVIS Assistant Integrations").
    *   Select a "Billing account" if prompted (many APIs have a free tier generous enough for personal use, but a billing account might be required to enable APIs).
    *   Select an "Organization" or "Location" if applicable, then click "CREATE".
3.  If you have an existing project you'd like to use, select it from the dropdown.

## 2. Enable Google Calendar API and Gmail API

1.  Make sure your project is selected in the GCP console.
2.  In the navigation menu (hamburger icon ☰) on the left, go to **APIs & Services > Library**.
3.  **Enable Google Calendar API:**
    *   In the search bar, type "Google Calendar API" and select it from the results.
    *   Click the "Enable" button. If it's already enabled, you'll see "Manage".
4.  **Enable Gmail API:**
    *   Go back to **APIs & Services > Library**.
    *   In the search bar, type "Gmail API" and select it from the results.
    *   Click the "Enable" button.

## 3. Configure OAuth Consent Screen

Before creating credentials, you need to configure the OAuth consent screen. This is what you'll see when J.A.R.V.I.S. asks for permission to access your data.

1.  In the navigation menu, go to **APIs & Services > OAuth consent screen**.
2.  **User Type:**
    *   Choose **External** if you are using a personal Gmail account (not a Google Workspace account).
    *   Choose **Internal** if you are using a Google Workspace account and only users within your organization will use this. (For most personal users, **External** is appropriate).
    *   Click "CREATE".
3.  **App information:**
    *   **App name:** Enter a name, e.g., "J.A.R.V.I.S. Assistant".
    *   **User support email:** Select your email address.
    *   **App logo:** (Optional)
4.  **Developer contact information:**
    *   Enter your email address.
    *   Click "SAVE AND CONTINUE".
5.  **Scopes:**
    *   You *can* add scopes here, but it's often easier to let the application request them. For now, you can click "SAVE AND CONTINUE" without adding scopes. The application will request the necessary scopes during the authorization flow.
    *   The application will request scopes like:
        *   `https://www.googleapis.com/auth/calendar` (for full calendar access) or `https://www.googleapis.com/auth/calendar.readonly` (for read-only).
        *   `https://www.googleapis.com/auth/gmail.readonly` (for reading emails).
6.  **Test users:**
    *   If you selected "External" for User Type and your app is in "Testing" publishing status (which is the default), you **must** add your Google account email address as a test user. Otherwise, you won't be able to grant consent.
    *   Click "+ ADD USERS".
    *   Enter your Google email address(es).
    *   Click "ADD".
    *   Click "SAVE AND CONTINUE".
7.  **Summary:** Review the summary and click "BACK TO DASHBOARD".
    *   Initially, your app will be in "Testing" mode. For personal use, this is fine. If you were to release this more broadly, you'd need to submit it for verification.

## 4. Create OAuth 2.0 Credentials

1.  In the navigation menu, go to **APIs & Services > Credentials**.
2.  Click "+ CREATE CREDENTIALS" at the top of the page.
3.  Select **OAuth client ID**.
4.  **Application type:**
    *   Choose **Desktop app**. (J.A.R.V.I.S. runs locally as a desktop application).
5.  **Name:**
    *   Enter a name for your desktop client, e.g., "JARVIS Desktop Client".
    *   Click "CREATE".
6.  **OAuth client created:**
    *   A dialog will appear showing your "Client ID" and "Client secret". **You don't need to copy these directly from here.**
    *   Click **DOWNLOAD JSON** on the right side of the client ID entry (or after clicking the client ID name). This will download a JSON file, often named `client_secret_XXXXXXXX....json`.
    *   Click "OK".

## 5. Place the Credentials File

1.  **Rename the downloaded JSON file** to `client_secret.json`.
2.  **Place this `client_secret.json` file** in the root directory of your J.A.R.V.I.S. assistant project (i.e., the `jarvis_assistant` folder where `main.py` is located).

    ```
    jarvis_assistant/
    ├── client_secret.json  <-- Place it here
    ├── core/
    ├── docs/
    │   └── google_api_setup.md
    ├── modules/
    ├── main.py
    ├── web_server.py
    └── ...
    ```

    **Important Security Note:** This `client_secret.json` file contains sensitive information. Ensure it is **NEVER** committed to public Git repositories. The `.gitignore` file in this project should already be configured to ignore it, but always double-check.

You have now configured the necessary Google Cloud Platform project and credentials for J.A.R.V.I.S. The application will use this `client_secret.json` file to initiate the OAuth 2.0 flow when you first use a Google Calendar or Gmail feature. You will be prompted in your browser to grant permission.Tool output for `create_file_with_block`:
