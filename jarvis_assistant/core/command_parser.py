# LLM interaction, intent recognition
import google.generativeai as genai
from jarvis_assistant.config import GEMINI_API_KEY
from jarvis_assistant.utils.logger import get_logger
import json

# Ensure get_logger can be found if this module is run standalone for testing
if __name__ == '__main__' and __package__ is None:
    import sys
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from jarvis_assistant.utils.logger import get_logger

class CommandParser:
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
            self.logger.error("Gemini API key not configured in config.py")
            raise ValueError("Gemini API key not configured. Please set it in config.py")

        genai.configure(api_key=GEMINI_API_KEY)
        # Specifying JSON mode if available and appropriate for the model
        # For 'gemini-pro', direct JSON mode is not explicitly listed in basic docs,
        # but we can instruct it to output JSON via prompt.
        # If using a model version that explicitly supports JSON output type, that's better.
        # For now, we'll use prompt engineering for JSON.
        self.model = genai.GenerativeModel('models/gemini-1.5-flash')
        self.logger.info("CommandParser initialized with Gemini model models/gemini-1.5-flash.")

    def _build_prompt(self, text_command: str) -> str:
        # This prompt needs to be carefully crafted and tested.
        # It instructs the LLM to return a JSON object.
        prompt = f"""
Analyze the following user command and extract the primary intent and relevant entities.
Your response MUST be a single valid JSON object. Do not include any text before or after the JSON object.

The JSON object should have two main keys: "intent" and "entities".

"intent" should be a string from the following list (or "unknown" if not applicable):
  - "create_file"  # Generic file creation, entities will specify type (txt, doc, sheet)
  - "create_directory"
  - "delete_path"
  - "move_path"
  - "list_directory_contents"
  - "execute_command"
  - "set_brightness"
  - "set_volume"
  - "open_app"
  - "close_app"
  - "open_website"
  - "search_info"
  - "summarize_text" # New intent for summarizing provided text or web page content
  - "media_play"
  - "media_pause"
  - "media_skip"
  - "media_previous" # Can also be "rewind" or "go back"
  - "fill_web_form" # For Phase 2
  - "simulate_online_purchase" # For Phase 2 (simulation only)
  - "general_query" (for things like "what time is it?" or "tell me a joke")
  - "store_auth_info" # For security manager interaction
  - "get_auth_info" # For security manager interaction
  - "exit"

"entities" should be a JSON object containing relevant extracted information. Examples:
  - For "create_file": {{"filepath": "path/to/file.ext", "content": "optional file content here", "file_type": "txt/document/spreadsheet"}} (default file_type to "txt" if not clear)
  - For "create_directory": {{"dir_path": "path/to/directory"}}
  - For "delete_path": {{"path": "path/to/delete"}}
  - For "move_path": {{"source_path": "path/to/source", "destination_path": "path/to/destination"}}
  - For "list_directory_contents": {{"dir_path": "path/to/list"}}
  - For "execute_command": {{"command_str": "the command to run (can be multi-line)", "shell_type": "cmd/powershell/bash/sh/zsh"}} (default shell_type appropriately by OS if not specified)
  - For "set_brightness": {{"level": 75}} (integer 0-100, e.g., "set brightness to 75%", "dim screen to 20")
  - For "set_volume": {{"level": 0.5}} (float 0.0-1.0, e.g. "set volume to 50%" means level 0.5, "mute" means level 0.0, "max volume" means 1.0)
  - For "open_app": {{"app_name": "application name or path"}}
  - For "close_app": {{"app_name": "application name or process name"}}
  - For "open_website": {{"url": "website_url.com (try to make it a full URL like http://...)"}}
  - For "search_info": {{"query": "search query", "summarize": true/false}} (default summarize to false; if true, the main app will call summarize_text after search)
  - For "summarize_text": {{"text_to_summarize": "long text here", "source_url": "optional_url_if_text_is_from_webpage"}}
  - For "media_play": {{"player_name": "spotify/apple music/native/default etc.", "track_or_playlist": "optional track/playlist name"}}
  - For "media_pause": {{"player_name": "spotify/apple music/native/default etc."}}
  - For "media_skip": {{"player_name": "spotify/apple music/native/default etc."}} (for "next track")
  - For "media_previous": {{"player_name": "spotify/apple music/native/default etc."}} (for "previous track" or "rewind")
  - For "fill_web_form": {{"url": "target_url", "form_type_identifier": "e.g., generic_registration, specific_site_login", "data_profile_key": "key_for_security_manager_data"}}
  - For "simulate_online_purchase": {{"item_description": "item to search for", "site_url": "optional_target_site", "dummy_data_profile_key": "key_for_security_manager_test_data"}}
  - For "general_query": {{"query_text": "full user query"}}
  - For "store_auth_info": {{"service_name": "service identifier", "username": "user's name for the service", "data_to_store": "the sensitive data/password"}}
  - For "get_auth_info": {{"service_name": "service identifier", "username": "user's name for the service"}}
  - For "exit": {{}}

General Instructions for Entity Extraction:
- File Paths: If a user says "my documents" or "desktop", try to map these to standard user directory paths. If a path is relative, keep it relative unless easily resolvable to an absolute one. For file creation, try to infer the file extension if not explicitly given but a file type (document, spreadsheet) is mentioned.
- Application Names: Be flexible. "Word" could be "Microsoft Word".
- URLs: If a user says "google.com", convert to "http://google.com" or "https://google.com".
- Percentages: For brightness/volume, convert "75 percent" or "half" to the numerical target format.
- Complex Commands: For "execute_command", the "command_str" can contain newlines if the user dictates a multi-line script.
- Summarization: If the user asks to search AND summarize, the intent should be "search_info" with "summarize": true. The main application flow will then handle getting the content and calling a "summarize_text" action. If the user provides text directly or points to a page to summarize, use "summarize_text".
- Media Player: If no player is specified, use a sensible default like "default" or "native". "Rewind" can map to "media_previous" or a specific player's rewind function if that level of detail is later supported.

User command: "{text_command}"

JSON Response:
"""
        return prompt

    def parse_command(self, text_command: str) -> dict:
        """
        Uses the LLM to understand the user's command and returns a structured dictionary.
        """
        prompt = self._build_prompt(text_command)
        self.logger.debug(f"Generated prompt for LLM: {prompt}")

        try:
            # Configuration for Gemini to encourage JSON output (though not strictly enforcing via API param here)
            generation_config = genai.types.GenerationConfig(
                # response_mime_type="application/json", # Not available for gemini-pro directly this way
                temperature=0.1 # Lower temperature for more deterministic JSON structure
            )
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )

            raw_response_text = response.text
            self.logger.info(f"Raw LLM response: {raw_response_text}")

            # Clean the response: LLMs sometimes wrap JSON in ```json ... ```
            cleaned_response_text = raw_response_text.strip()
            if cleaned_response_text.startswith("```json"):
                cleaned_response_text = cleaned_response_text[7:]
            if cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[:-3]
            cleaned_response_text = cleaned_response_text.strip()

            # Attempt to parse the cleaned text as JSON
            parsed_json = json.loads(cleaned_response_text)

            if "intent" not in parsed_json or "entities" not in parsed_json:
                self.logger.warning(f"LLM response missing 'intent' or 'entities': {parsed_json}")
                return {"intent": "unknown", "entities": {"error": "Malformed JSON structure from LLM."}}

            self.logger.info(f"Successfully parsed LLM response into JSON: {parsed_json}")
            return parsed_json

        except json.JSONDecodeError as je:
            self.logger.error(f"Failed to decode LLM response as JSON. Error: {je}. Response was: {raw_response_text}")
            return {"intent": "unknown", "entities": {"error": "LLM response was not valid JSON.", "raw_response": raw_response_text}}
        except Exception as e:
            self.logger.error(f"Error parsing command with LLM: {e}", exc_info=True)
            return {"intent": "unknown", "entities": {"error": f"An unexpected error occurred: {str(e)}"}}

if __name__ == '__main__':
    # Ensure config.py has a valid API key for this test to run
    # You might need to set up PYTHONPATH or run this from the project root for imports to work easily.
    # Example: python -m jarvis_assistant.core.command_parser

    try:
        parser = CommandParser()
        commands_to_test = [
            "create a document called report.txt with content This is my report.",
            "make a spreadsheet named budget",
            "run the command ls -la in my home directory using bash",
            "search for python programming tutorials and summarize them",
            "summarize this article from https://example.com/article",
            "play the album dark side of the moon on spotify",
            "open my custom editor",
            "increase screen brightness to 90%",
            "set master volume to half",
            "what is the weather like today?", # general_query
            "exit"
        ]

        expected_intents = [
            "create_file",
            "create_file",
            "execute_command",
            "search_info", # summarize: True will be an entity
            "summarize_text", # Assuming the LLM can distinguish this from search_info based on phrasing
            "media_play",
            "open_app",
            "set_brightness",
            "set_volume",
            "general_query",
            "exit"
        ]

        for i, command in enumerate(commands_to_test):
            print(f"\n--- Testing Command: '{command}' ---")
            parsed_output = parser.parse_command(command)
            print(f"Parsed Output: {json.dumps(parsed_output, indent=2)}")
            # Basic validation
            assert "intent" in parsed_output
            assert "entities" in parsed_output
            if parsed_output["intent"] != "unknown":
                print(f"Intent: {parsed_output['intent']}")
            else:
                 print(f"WARNING: Intent was 'unknown' for command: {command}")


    except ValueError as ve: # API key error
        print(f"Setup Error: {ve}")
    except ImportError as ie:
        print(f"Import Error: {ie}. Ensure you are running this test from the project root or have PYTHONPATH set.")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")
