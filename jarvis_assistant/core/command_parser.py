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
        self.model = genai.GenerativeModel('models/gemini-1.5-flash')
        self.logger.info("CommandParser initialized with Gemini model models/gemini-1.5-flash.")

    def _build_prompt(self, text_command: str) -> str:
        prompt = f"""
Analyze the following user command and extract the primary intent and relevant entities.
Your response MUST be a single valid JSON object. Do not include any text before or after the JSON object.

The JSON object should have two main keys: "intent" and "entities".

"intent" should be a string from the following list (or "unknown" if not applicable):
  - "create_file"
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
  - "summarize_text"
  - "media_play"
  - "media_pause"
  - "media_skip"
  - "media_previous"
  - "fill_web_form"
  - "simulate_online_purchase"
  - "general_query"
  - "store_auth_info"
  - "get_auth_info"
  - "list_calendar_events"
  - "create_calendar_event"
  - "exit"

"entities" should be a JSON object containing relevant extracted information. Examples:
  - For "create_file": {{"filepath": "path/to/file.ext", "content": "optional file content here", "file_type": "txt/document/spreadsheet"}}
  - For "create_directory": {{"dir_path": "path/to/directory"}}
  - For "delete_path": {{"path": "path/to/delete"}}
  - For "move_path": {{"source_path": "path/to/source", "destination_path": "path/to/destination"}}
  - For "list_directory_contents": {{"dir_path": "path/to/list"}}
  - For "execute_command": {{"command_str": "the command to run", "shell_type": "cmd/powershell/bash/sh/zsh"}}
  - For "set_brightness": {{"level": 75}}
  - For "set_volume": {{"level": 0.5}}
  - For "open_app": {{"app_name": "application name or path"}}
  - For "close_app": {{"app_name": "application name or process name"}}
  - For "open_website": {{"url": "website_url.com"}}
  - For "search_info": {{"query": "search query", "summarize": true/false}}
  - For "summarize_text": {{"text_to_summarize": "long text here", "source_url": "optional_url_if_text_is_from_webpage"}}
  - For "media_play": {{"player_name": "spotify/default", "track_or_playlist": "optional track/playlist name"}}
  - For "media_pause": {{"player_name": "spotify/default"}}
  - For "media_skip": {{"player_name": "spotify/default"}}
  - For "media_previous": {{"player_name": "spotify/default"}}
  - For "fill_web_form": {{"url": "target_url", "form_type_identifier": "e.g., generic_registration", "data_profile_key": "key_for_security_manager_data"}}
  - For "simulate_online_purchase": {{"item_description": "item to search for", "site_url": "optional_target_site", "dummy_data_profile_key": "key_for_security_manager_test_data"}}
  - For "general_query": {{"query_text": "full user query"}}
  - For "store_auth_info": {{"service_name": "service identifier", "username": "user's name for the service", "data_to_store": "the sensitive data/password"}}
  - For "get_auth_info": {{"service_name": "service identifier", "username": "user's name for the service"}}
  - For "list_calendar_events": {{"time_period": "today/tomorrow/next 7 days/YYYY-MM-DD", "max_results": 10}} (time_period is flexible, default to "today" or "next 7 days". max_results is optional, default to 10-15)
  - For "create_calendar_event": {{"summary": "Event title", "start_datetime_iso": "YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS±HH:MM or YYYY-MM-DD for all-day", "end_datetime_iso": "YYYY-MM-DDTHH:MM:SSZ or YYYY-MM-DDTHH:MM:SS±HH:MM or YYYY-MM-DD for all-day", "description": "Optional event description", "attendees": ["email1@example.com", "email2@example.com"]}} (attendees is optional. For dates/times, try to convert natural language like "tomorrow 2pm" to ISO 8601. If only a start time is given for a typical short event, assume a 1-hour duration for end time. For all-day events, only date part YYYY-MM-DD is needed for start and end (end date is exclusive for multi-day all-day events, or same as start for single all-day). If timezone is not specified, assume user's local timezone or UTC if that's easier.)
  - For "exit": {{}}

General Instructions for Entity Extraction:
- File Paths: If a user says "my documents" or "desktop", try to map these to standard user directory paths.
- URLs: If a user says "google.com", convert to "http://google.com" or "https://google.com".
- Percentages: For brightness/volume, convert "75 percent" or "half" to the numerical target format.
- Calendar Date/Time: For "create_calendar_event", it is crucial to get `start_datetime_iso` and `end_datetime_iso`. If the user says "meeting tomorrow at 2pm", determine today's date to make "tomorrow" absolute. If no duration is given, assume 1 hour for meetings. If a date is given without a time (e.g. "dentist appointment on July 26th"), treat it as an all-day event for that date (e.g., start: "YYYY-MM-DD", end: "YYYY-MM-DD"). Timezone handling can be complex; if user specifies a timezone, include it in ISO format (e.g. "-07:00" or "Z" for UTC). If not, the application might assume user's local timezone when processing. For "list_calendar_events", "time_period" can be "today", "tomorrow", "next week", "this month", or a specific date "July 26th".

User command: "{text_command}"

JSON Response:
"""
        return prompt

    def parse_command(self, text_command: str) -> dict:
        prompt = self._build_prompt(text_command)
        self.logger.debug(f"Generated prompt for LLM: {prompt}")

        try:
            generation_config = genai.types.GenerationConfig(
                temperature=0.1
            )
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )

            raw_response_text = response.text
            self.logger.info(f"Raw LLM response: {raw_response_text}")

            cleaned_response_text = raw_response_text.strip()
            if cleaned_response_text.startswith("```json"):
                cleaned_response_text = cleaned_response_text[7:]
            if cleaned_response_text.endswith("```"):
                cleaned_response_text = cleaned_response_text[:-3]
            cleaned_response_text = cleaned_response_text.strip()

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
            "what is the weather like today?",
            "exit",
            "what's on my calendar for tomorrow?",
            "show me my appointments for today",
            "create a calendar event: Lunch with Bob on August 15th at 1pm for 1 hour",
            "add an event to my calendar: Doctor's appointment on 2024-09-10 from 3 PM to 3:30 PM, description: Annual checkup"
        ]

        # Expected intents can be used for more rigorous testing if desired
        # expected_intents = [
        #     "create_file", "create_file", "execute_command", "search_info",
        #     "summarize_text", "media_play", "open_app", "set_brightness",
        #     "set_volume", "general_query", "exit", "list_calendar_events",
        #     "list_calendar_events", "create_calendar_event", "create_calendar_event"
        # ]

        for i, command in enumerate(commands_to_test):
            print(f"\n--- Testing Command: '{command}' ---")
            parsed_output = parser.parse_command(command)
            print(f"Parsed Output: {json.dumps(parsed_output, indent=2)}")
            assert "intent" in parsed_output
            assert "entities" in parsed_output
            if parsed_output["intent"] == "unknown" and "error" not in parsed_output["entities"]:
                 print(f"WARNING: Intent was 'unknown' but no specific error reported for command: {command}")
            elif parsed_output["intent"] == "unknown" and "error" in parsed_output["entities"]:
                 print(f"INFO: Intent was 'unknown' with error: {parsed_output['entities']['error']}")
            else:
                print(f"Intent: {parsed_output['intent']}")

    except ValueError as ve:
        print(f"Setup Error: {ve}")
    except ImportError as ie:
        print(f"Import Error: {ie}. Ensure you are running this test from the project root or have PYTHONPATH set.")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")
