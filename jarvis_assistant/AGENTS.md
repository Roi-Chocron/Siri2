# AGENTS.md - Instructions for AI Agents

Welcome, AI Developer! This document provides guidelines for working on the J.A.R.V.I.S. assistant project.

## Project Structure

The project is organized into the following main directories:

*   `core/`: Contains essential services like speech recognition, text-to-speech, command parsing (LLM interaction), and security management.
*   `modules/`: Houses specific functionalities such as OS interaction, application management, web automation, and media control. Each module should be as self-contained as possible.
*   `utils/`: For helper utilities like logging.
*   `config.py`: Stores configuration variables, notably API keys. **Never commit real API keys directly into this file if the project were to be public. Use environment variables or a .env file for production-like setups.** For this development environment, it's acceptable for the user to place their key here.
*   `main.py`: The entry point of the application.

## Development Principles

1.  **Modularity:** Strive to keep modules independent. If a module needs a service from `core`, it should import it. Avoid deep interdependencies between modules in the `modules/` directory.
2.  **Platform Agnosticism (where feasible):** While some features are inherently OS-specific (e.g., precise volume control), try to use cross-platform libraries (`os`, `subprocess`, `psutil`) where possible. Clearly document OS-specific sections or libraries.
    *   For OS-specific libraries (like `pycaw` for Windows volume, `screen_brightness_control`), ensure they are commented out in `requirements.txt` by default or provide clear instructions, as they might fail to install or run on other OSes. The implementation should gracefully handle their absence if a user is on an unsupported OS for that specific feature.
3.  **Security First:**
    *   **Sensitive Data:** All sensitive user data (credentials, personal info for forms, API keys beyond the main Gemini key) MUST be handled through the `SecurityManager` which uses the `keyring` library. Do not store such data in plain text files or hardcode it.
    *   **Financial Transactions:** This is a high-risk area. Any development towards online purchasing MUST prioritize security. User authentication must be robust (the current `getpass` is a placeholder and NOT sufficient). Avoid storing full payment details if possible; prefer tokenization or payment gateway APIs if explored. For this project, simulation is preferred over actual transactions.
    *   **Command Execution:** Be extremely cautious with commands received from the LLM that are intended for execution via `subprocess` (e.g., in `os_interaction.py`). While the LLM parses commands, the final execution string should ideally be constructed from recognized intents and entities, not directly from raw LLM output if that output could be arbitrarily complex or malicious. For now, we are trusting the LLM's parsed output structure, but this is an area for future hardening.
4.  **Error Handling:** Implement robust error handling in all modules. Inform the user clearly if an action cannot be performed. Log errors to the `logs/` directory using the provided logger.
5.  **Configuration:** The primary Gemini API key is configured in `config.py`. Other user preferences can also be added there.
6.  **Dependencies:** Add new Python dependencies to `jarvis_assistant/requirements.txt`.
7.  **LLM Interaction:**
    *   The `CommandParser` in `core/` is the primary interface to the Gemini API.
    *   Prompt engineering will be crucial. Prompts should be designed to extract clear intents and entities from user commands.
    *   For complex tasks, consider a multi-step conversation with the LLM or chained LLM calls.
8.  **Placeholders:** The initial setup includes many placeholder comments (e.g., `# Placeholder`, `# TODO`). Address these as you implement features. Remove the placeholder comment once the functionality is substantially implemented.

## Running and Testing

*   Run the main application using `python jarvis_assistant/main.py`.
*   Each module has a `if __name__ == '__main__':` block for basic standalone testing of its core functionalities. Use this for unit testing during development.
*   When adding new features, ensure they are covered by these standalone tests if possible.

## Code Style

*   Follow PEP 8 Python style guidelines.
*   Use clear and descriptive variable and function names.
*   Add comments to explain complex logic or non-obvious decisions.

## Specific Module Notes

*   **`AppManager`**:
    *   Finding application paths automatically is challenging. The `_find_app_path` method uses heuristics including PATH search, common OS-specific directories (e.g., Program Files on Windows, /Applications on macOS), and limited scanning within matched application folders.
    *   This heuristic approach works for many common desktop applications but has limitations. It will likely **not** automatically discover or correctly launch:
        *   Applications installed via the Microsoft Store (which require special shell commands).
        *   Games or applications managed by complex launchers (e.g., Steam, EA App, Epic Games Store) which might need specific launcher commands or AppIDs.
        *   Applications with highly non-standard installation paths or obscure executable names.
    *   For reliable launching of problematic applications, users **must** utilize the `USER_APP_PATHS` dictionary in `jarvis_assistant/config.py` to provide explicit aliases and full paths to the executables.
    *   Future enhancements could involve more advanced OS-specific discovery methods like registry scanning (Windows) or Start Menu parsing.
*   **`MediaController`**: Direct media player control is highly OS and player-dependent. The current version uses `osascript` for macOS and `playerctl` for Linux (for Spotify) as examples. These are not universally available. Robust media control might require dedicated libraries or APIs (e.g., Spotify Web API).
*   **`WebAutomator`**:
    *   Web scraping for search summarization is fragile and depends on the search engine's HTML structure. Using an LLM to summarize content from a fetched page would be more robust if the LLM can process full HTML or extracted text.
    *   Selenium-based automation requires WebDriver setup by the user. Ensure this is clearly communicated.

By following these guidelines, we can build a powerful and reasonably secure AI assistant. Good luck!
