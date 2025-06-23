# J.A.R.V.I.S. - AI Powered Computer Control System

This project is an advanced AI-powered computer control system, designed to function as a personal virtual assistant. It leverages Large Language Models (LLMs) for natural language understanding and aims to provide seamless interaction with the operating system and various applications through voice and text commands.

## Features (Planned)

*   **Operating System Interaction:**
    *   Manage files and folders.
    *   Create text files, documents, and spreadsheets with dictated content.
    *   Execute CMD and PowerShell commands.
    *   Control system settings (brightness, volume).
*   **Application and Media Management:**
    *   Open and close installed software.
    *   Control media players (play, pause, skip, rewind).`
*   **Web Interaction:**
    *   Open specific websites.
    *   Perform information searches and summarize results.
*   **Advanced Web Automation:**
    *   Fill online registration forms using securely provided details.
    *   (Exploratory) Perform online purchases securely.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd jarvis_assistant
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Some dependencies like `pycaw` (for Windows volume control) or `screen_brightness_control` might have system-level requirements or are OS-specific. `SpeechRecognition` might require `portaudio` for microphone access on some systems (`sudo apt-get install portaudio19-dev` on Debian/Ubuntu).*

4.  **Configure API Key:**
    *   Open `jarvis_assistant/config.py`.
    *   Replace `"YOUR_GEMINI_API_KEY"` with your actual Gemini API key.
    ```python
    GEMINI_API_KEY = "your_actual_api_key_here"
    ```

5.  **WebDriver (for advanced web automation):**
    *   If you plan to use features like form filling or online purchases, Selenium WebDriver is required.
    *   Download the appropriate WebDriver for your browser (e.g., ChromeDriver for Chrome) and ensure it's in your system's PATH or specify its location in the `WebAutomator` module if needed.
    *   `webdriver-manager` can help automate this: `pip install webdriver-manager`. The code has placeholder comments for its usage.

## Running the Assistant

```bash
python jarvis_assistant/main.py
```

## Security Note on Sensitive Data

*   The `SecurityManager` uses the `keyring` library to store sensitive information (like personal details for form filling, potential payment info placeholders) in your operating system's credential manager. This is generally more secure than storing plaintext in config files.
*   **Financial Transactions:** The functionality for online purchases is highly experimental and carries significant security risks. The current implementation will include strong disclaimers and placeholders. **Extreme caution is advised, and it should not be used with real financial information without extensive security audits and enhancements.** A robust multi-factor authentication will be designed before any such feature is seriously considered for anything beyond a conceptual demonstration.

## Modules Overview

*   `main.py`: Main application entry point.
*   `config.py`: Configuration like API keys.
*   `core/`: Core components:
    *   `command_parser.py`: LLM integration for understanding commands.
    *   `speech_recognizer.py`: Voice input handling.
    *   `text_to_speech.py`: Voice output handling.
    *   `security_manager.py`: Secure storage and authentication.
*   `modules/`: Functional modules:
    *   `os_interaction.py`: File/system operations.
    *   `app_manager.py`: Application control.
    *   `web_automator.py`: Web browsing and automation.
    *   `media_controller.py`: Media playback control.
*   `utils/`: Utility scripts, e.g., `logger.py`.
*   `logs/`: Directory where log files will be stored.

## Contributing
(Placeholder for contribution guidelines if this were a public project)

---
*Disclaimer: This is a software development project. Features involving financial transactions and sensitive data handling are complex and require rigorous security measures. This project aims to explore these capabilities, prioritizing security best practices, but users should be aware of potential risks.*
