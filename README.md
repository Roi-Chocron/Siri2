# Siri2 - J.A.R.V.I.S. Assistant

This project is a Python-based virtual assistant named J.A.R.V.I.S. (Just A Rather Very Intelligent System).

## Features (Planned and In-Progress)

*   Voice command recognition
*   Text-to-speech responses
*   OS Interaction (file/directory management, command execution)
*   Application launching
*   Web searching and browsing
*   Media control
*   (Future) Web form filling, simulated online purchases
*   (Future) Secure credential management

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd Siri2-1 # Or your project directory name
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r jarvis_assistant/requirements.txt
    ```
    *Note: Some OS-specific dependencies like `pycaw` (for Windows volume control) or `screen_brightness_control` might cause issues on other platforms if not handled gracefully by the application or if their installation fails. The application aims to catch ImportErrors for such cases.*

4.  **Configure API Key:**
    *   Open `jarvis_assistant/config.py`.
    *   Replace `"YOUR_GEMINI_API_KEY"` with your actual Google Gemini API key.
    ```python
    GEMINI_API_KEY = "YOUR_ACTUAL_GEMINI_API_KEY_HERE"
    ```

## Running the Assistant

To run the J.A.R.V.I.S. assistant, navigate to the root directory of the project (e.g., `Siri2-1/`) in your terminal and use the following command:

```bash
python -m jarvis_assistant.main
```

Using `python -m` ensures that the Python interpreter correctly handles the project as a package, which is necessary for the internal imports (like `from jarvis_assistant.core...`) to work as expected from any subdirectory or when the main script is inside a package. Running `python jarvis_assistant/main.py` directly from the root might lead to `ModuleNotFoundError` if the project root is not automatically added to Python's search path.

## Usage

Once running, the assistant will prompt you to speak or will listen for voice commands (depending on the current input mode, which defaults to voice).

Example commands:
*   "Open Notepad"
*   "Create a file named my_notes.txt in my documents folder"
*   "Search for Italian pasta recipes on Google"
*   "What time is it?" (General query, may have basic handling)
*   "Exit Jarvis"

## Project Structure

*   `jarvis_assistant/`: Main package directory.
    *   `core/`: Speech recognition, TTS, command parsing.
    *   `modules/`: OS interaction, app management, web automation, etc.
    *   `utils/`: Logging and other utilities.
    *   `config.py`: API keys and user configurations.
    *   `main.py`: Main application entry point.
    *   `AGENTS.md`: Instructions for AI developers working on this project.
*   `logs/`: Directory where log files are stored.
*   `README.md`: This file.

Refer to `jarvis_assistant/AGENTS.md` for more detailed developer guidelines.