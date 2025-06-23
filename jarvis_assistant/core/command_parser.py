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
        self.model = genai.GenerativeModel('gemini-pro')
        self.logger.info("CommandParser initialized with Gemini model.")

    def _build_prompt(self, text_command: str) -> str:
        # This prompt needs to be carefully crafted and tested.
        # It instructs the LLM to return a JSON object.
        prompt = f"""
Analyze the following user command and extract the primary intent and relevant entities.
Your response MUST be a single valid JSON object. Do not include any text before or after the JSON object.

The JSON object should have two main keys: "intent" and "entities".
"intent" should be a string from the following list (or "unknown" if not applicable):
  - "create_text_file"
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
  - "media_play"
  - "media_pause"
  - "media_skip"
  - "media_previous"
  - "general_query" (for things like "what time is it?" or "tell me a joke")
  - "exit"

"entities" should be a JSON object containing relevant extracted information. Examples:
  - For "create_text_file": {{"filepath": "path/to/file.txt", "content": "file content here"}}
  - For "create_directory": {{"dir_path": "path/to/directory"}}
  - For "delete_path": {{"path": "path/to/delete"}}
  - For "move_path": {{"source_path": "path/to/source", "destination_path": "path/to/destination"}}
  - For "list_directory_contents": {{"dir_path": "path/to/list"}}
  - For "execute_command": {{"command_str": "the command to run", "shell_type": "cmd/powershell/bash/sh/zsh"}} (default shell_type to "cmd" on Windows, "sh" on POSIX if not specified)
  - For "set_brightness": {{"level": 0-100}}
  - For "set_volume": {{"level": 0.0-1.0}} (e.g. "set volume to 50%" means level 0.5)
  - For "open_app": {{"app_name": "application name"}}
  - For "close_app": {{"app_name": "application name or exe"}}
  - For "open_website": {{"url": "website_url.com"}}
  - For "search_info": {{"query": "search query", "summarize": true/false}} (default summarize to false)
  - For "media_play": {{"player_name": "spotify/apple music/etc", "track_or_playlist": "optional track/playlist"}}
  - For "media_pause": {{"player_name": "spotify/apple music/etc"}}
  - For "media_skip": {{"player_name": "spotify/apple music/etc"}}
  - For "media_previous": {{"player_name": "spotify/apple music/etc"}}
  - For "general_query": {{"query_text": "full user query"}}
  - For "exit": {{}}

If a path is mentioned, try to make it absolute if possible, or specify if it's relative.
If a value is clearly a percentage for volume/brightness, convert it to the required format (0-100 for brightness, 0.0-1.0 for volume).
If no specific player is mentioned for media commands, you can try to infer or leave it null.
If no shell_type is mentioned for execute_command, default to "cmd" on Windows and "sh" on other OSes.

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
            "create a text file named my_notes.txt with content hello world",
            "make a new folder called important documents in my user directory",
            "delete the file temp.log",
            "move old_report.docx to the archive folder",
            "what files are in my downloads folder?",
            "run ipconfig in command prompt",
            "set brightness to 75 percent",
            "turn the volume up to 0.8",
            "open notepad",
            "close chrome",
            "go to google.com",
            "search for the weather in London and summarize it",
            "play my workout playlist on spotify",
            "pause spotify",
            "next song on spotify",
            "what time is it?",
            "exit jarvis now"
        ]

        for command in commands_to_test:
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
