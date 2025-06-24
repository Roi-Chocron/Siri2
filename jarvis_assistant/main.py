# Main application entry point
import time
from jarvis_assistant.core.speech_recognizer import SpeechRecognizer
from jarvis_assistant.core.text_to_speech import TextToSpeech
from jarvis_assistant.core.command_parser import CommandParser
from jarvis_assistant.modules.os_interaction import OSInteraction
from jarvis_assistant.modules.app_manager import AppManager
from jarvis_assistant.modules.media_controller import MediaController
from jarvis_assistant.modules.web_automator import WebAutomator
from jarvis_assistant.modules.google_calendar_manager import GoogleCalendarManager # Import Calendar Manager
from jarvis_assistant.utils.logger import get_logger
from jarvis_assistant.config import GEMINI_API_KEY
import os
import json # For potential error parsing from Google API

logger = get_logger("JARVIS_Main")

def handle_os_interaction(os_agent: OSInteraction, intent: str, entities: dict) -> str:
    """Handles OS interaction based on intent and entities."""
    response_message = "Sorry, I couldn't perform that OS action." # Default error
    # success = False # Not used directly, but methods in os_agent return it.

    if intent == "create_file":
        filepath = entities.get("filepath")
        content = entities.get("content", "")
        file_type = entities.get("file_type", "txt")
        if filepath:
            final_filepath_to_use = filepath
            if os.path.isabs(filepath):
                drive_abs, tail_abs = os.path.splitdrive(os.path.normpath(filepath))
                if (drive_abs and tail_abs.startswith(os.sep) and len(tail_abs.strip(os.sep).split(os.sep)) == 1) or \
                   (not drive_abs and filepath.startswith(os.sep) and len(filepath.strip(os.sep).split(os.sep)) == 1):
                    response_message = (
                        f"Creating files directly in a root directory like '{os.path.dirname(os.path.normpath(filepath))}' "
                        "is often restricted. Please try a path in your user folders."
                    )
                else:
                    _, response_message = os_agent.create_file(final_filepath_to_use, content, file_type)
            else:
                final_filepath_to_use = os.path.expanduser(os.path.join("~", filepath))
                _, response_message = os_agent.create_file(final_filepath_to_use, content, file_type)
        else:
            response_message = "I need a filepath to create a file."

    elif intent == "create_directory":
        dir_path = entities.get("dir_path")
        if dir_path:
            if not os.path.isabs(dir_path):
                dir_path = os.path.expanduser(os.path.join("~", dir_path))
            _, response_message = os_agent.create_directory(dir_path)
        else:
            response_message = "I need a directory path to create a directory."

    elif intent == "delete_path":
        path_to_delete = entities.get("path")
        if path_to_delete:
            if not os.path.isabs(path_to_delete):
                path_to_delete = os.path.expanduser(os.path.join("~", path_to_delete))
            _, response_message = os_agent.delete_path(path_to_delete)
        else:
            response_message = "I need a path to delete."

    elif intent == "move_path":
        source_path = entities.get("source_path")
        destination_path = entities.get("destination_path")
        if source_path and destination_path:
            if not os.path.isabs(source_path):
                source_path = os.path.expanduser(os.path.join("~", source_path))
            if not os.path.isabs(destination_path):
                destination_path = os.path.expanduser(os.path.join("~", destination_path))
            _, response_message = os_agent.move_path(source_path, destination_path)
        else:
            response_message = "I need both a source and a destination path to move."

    elif intent == "list_directory_contents":
        dir_path = entities.get("dir_path", "~")
        if not os.path.isabs(dir_path) and dir_path != "~":
             dir_path = os.path.expanduser(os.path.join("~", dir_path))
        elif dir_path == "~":
            dir_path = os.path.expanduser("~")

        success, result = os_agent.list_directory_contents(dir_path)
        if success:
            if isinstance(result, list):
                response_message = f"Contents of {dir_path}:\n" + "\n".join(result)
                if not result: response_message = f"The directory {dir_path} is empty."
            else:
                response_message = result
        else:
            response_message = result

    elif intent == "execute_command":
        command_str = entities.get("command_str")
        shell_type = entities.get("shell_type")
        if os.name == 'nt' and not shell_type:
            shell_type = "cmd"
        elif os.name != 'nt' and not shell_type:
            shell_type = "sh"

        if command_str:
            logger.warning(f"Executing potentially arbitrary command: {command_str} in {shell_type}")
            success, output = os_agent.execute_command(command_str, shell_type)
            response_message = f"Command executed. Output:\n{output}" if success else f"Command failed:\n{output}"
        else:
            response_message = "I need a command to execute."

    elif intent == "set_brightness":
        level = entities.get("level")
        if level is not None:
            try:
                level = int(level)
                _, response_message = os_agent.set_brightness(level)
            except ValueError:
                response_message = "Brightness level must be an integer."
        else:
            response_message = "I need a brightness level."

    elif intent == "set_volume":
        level = entities.get("level")
        if level is not None:
            try:
                level = float(level)
                _, response_message = os_agent.set_volume(level)
            except ValueError:
                response_message = "Volume level must be a number (e.g., 0.5 for 50%)."
        else:
            response_message = "I need a volume level."
    else:
        response_message = f"OS interaction for intent '{intent}' is not yet implemented."

    return response_message


def process_command_text(text_command: str, parser: CommandParser, os_agent: OSInteraction,
                         app_agent: AppManager, media_agent: MediaController, web_agent: WebAutomator,
                         calendar_agent: GoogleCalendarManager) -> str: # Added calendar_agent
    """
    Processes a text command and returns a response string.
    This function encapsulates the core command processing logic.
    """
    logger.info(f"Processing command: {text_command}")

    if "exit jarvis" in text_command.lower() or "quit jarvis" in text_command.lower():
        logger.info("Exit command recognized.")
        return "Goodbye!"

    parsed_action = parser.parse_command(text_command)
    logger.info(f"LLM parsed action: {parsed_action}")

    intent = parsed_action.get("intent", "unknown")
    entities = parsed_action.get("entities", {})
    response_message = ""

    if intent == "exit":
        logger.info("Exit intent recognized by LLM.")
        return "Goodbye!"

    elif intent in [
        "create_file", "create_directory", "delete_path",
        "move_path", "list_directory_contents", "execute_command",
        "set_brightness", "set_volume"
    ]:
        response_message = handle_os_interaction(os_agent, intent, entities)

    elif intent == "open_app":
        app_name = entities.get("app_name")
        if app_name:
            if app_agent.open_app(app_name):
                response_message = f"Opening {app_name}."
            else:
                if os.name == 'nt' and app_name.lower() == "microsoft store":
                    response_message = "Opening the Microsoft Store programmatically is complex..."
                else:
                    response_message = (f"Sorry, I couldn't open '{app_name}'. Ensure it's installed...")
        else:
            response_message = "Which application would you like to open?"

    elif intent == "close_app":
        app_name = entities.get("app_name")
        if app_name:
            if app_agent.close_app(app_name):
                response_message = f"Attempting to close {app_name}."
            else:
                response_message = f"Sorry, I couldn't close {app_name} or it wasn't running."
        else:
            response_message = "Which application would you like to close?"

    elif intent == "open_website":
        url = entities.get("url")
        if url:
            if web_agent.open_website(url):
                response_message = f"Opening {url}."
            else:
                response_message = f"Sorry, I couldn't open {url}."
        else:
            response_message = "Which website would you like to open?"

    elif intent == "search_info":
        query = entities.get("query")
        summarize = entities.get("summarize", False)
        if query:
            search_result = web_agent.search_info(query, summarize)
            if summarize:
                response_message = f"Here's what I found about {query}: {search_result}"
            else:
                response_message = f"I've opened a browser tab with search results for {query}."
        else:
            response_message = "What would you like me to search for?"

    elif intent in ["media_play", "media_pause", "media_skip", "media_previous"]:
        player_name = entities.get("player_name", "default")
        track_or_playlist = entities.get("track_or_playlist") # Only for media_play
        success, msg = False, "Media command not fully processed."
        if intent == "media_play": success, msg = media_agent.play(player_name, track_or_playlist)
        elif intent == "media_pause": success, msg = media_agent.pause(player_name)
        elif intent == "media_skip": success, msg = media_agent.skip_track(player_name)
        elif intent == "media_previous": success, msg = media_agent.previous_track(player_name)
        response_message = msg

    elif intent == "general_query":
        query_text = entities.get("query_text", text_command)
        # ... (existing general_query logic) ...
        response_message = f"Regarding your query: {query_text}... I'm still learning to handle general conversation."


    elif intent == "summarize_text":
        # ... (existing summarize_text logic) ...
        response_message = "Text summarization needs to be fully connected."

    # Google Calendar Intents
    elif intent == "list_calendar_events":
        if not calendar_agent:
            response_message = "Calendar functions are unavailable due to an earlier initialization error."
        else:
            time_period = entities.get("time_period", "next 7 days")
            max_results_str = entities.get("max_results", "10")
            try:
                max_results = int(max_results_str)
            except ValueError:
                max_results = 10
                logger.warning(f"Invalid max_results '{max_results_str}', defaulting to 10.")

            try:
                events, status_msg = calendar_agent.list_upcoming_events(
                    max_results=max_results,
                    time_period_str=time_period
                )
                if events:
                    response_message = f"{status_msg}\nUpcoming events:\n" + "\n".join(events)
                else:
                    response_message = status_msg
            except ConnectionError as ce:
                logger.error(f"Calendar connection error: {ce}")
                response_message = "Sorry, I couldn't connect to your calendar. Please ensure authentication is complete and try again."
            except Exception as e:
                logger.error(f"Error listing calendar events: {e}", exc_info=True)
                response_message = f"Sorry, I encountered an error trying to list calendar events: {e}"

    elif intent == "create_calendar_event":
        if not calendar_agent:
            response_message = "Calendar functions are unavailable due to an earlier initialization error."
        else:
            summary = entities.get("summary")
            start_datetime_iso = entities.get("start_datetime_iso")
            end_datetime_iso = entities.get("end_datetime_iso")
            description = entities.get("description")
            attendees = entities.get("attendees")

            if not summary or not start_datetime_iso or not end_datetime_iso:
                response_message = "To create an event, I need at least a summary, a start time, and an end time."
            else:
                try:
                    created_event, status_msg = calendar_agent.create_event(
                        summary=summary,
                        start_datetime_iso=start_datetime_iso,
                        end_datetime_iso=end_datetime_iso,
                        description=description,
                        attendees=attendees
                    )
                    response_message = status_msg
                except ConnectionError as ce:
                    logger.error(f"Calendar connection error: {ce}")
                    response_message = "Sorry, I couldn't connect to your calendar to create the event. Please ensure authentication is complete."
                except Exception as e:
                    logger.error(f"Error creating calendar event: {e}", exc_info=True)
                    response_message = f"Sorry, I encountered an error trying to create the calendar event: {e}"

    elif intent == "unknown":
        response_message = "I'm not sure how to handle that command. Could you try rephrasing?"
        if "error" in entities: # If LLM itself had an issue producing JSON
            response_message += f" (Parser error: {entities['error']})"
    else: # Fallback for intents defined in LLM but not yet handled here
        response_message = f"I understood the intent as '{intent}', but I don't know how to do that yet."

    return response_message


def main_loop():
    logger.info("J.A.R.V.I.S. Assistant Initializing for CLI mode...")
    calendar_agent = None # Initialize to None

    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        logger.error("Gemini API key not configured...")
        print("CRITICAL ERROR: Gemini API key not configured...")
        return

    try:
        recognizer = SpeechRecognizer()
        tts = TextToSpeech()
        parser = CommandParser()
        os_agent = OSInteraction()
        app_agent = AppManager()
        media_agent = MediaController()
        web_agent = WebAutomator()
        # Initialize Calendar Manager - this can trigger OAuth flow on first run
        # Set read_only=False to allow creating events.
        calendar_agent = GoogleCalendarManager(read_only=False)
        logger.info("Core components initialized for CLI mode.")
        tts.speak("J.A.R.V.I.S. online and ready.")
    except FileNotFoundError as fnf:
        logger.error(f"Initialization failed: {fnf}. This might be the client_secret.json for Google services.")
        print(f"ERROR: {fnf}. Please ensure 'client_secret.json' is set up correctly for Google services.")
        if 'tts' in locals(): tts.speak("Error during initialization. Some features might be unavailable. Check logs.")
        # calendar_agent remains None, features requiring it will be disabled.
    except ConnectionError as ce:
        logger.error(f"Google Authentication/Connection error during init: {ce}")
        print(f"ERROR: Could not connect to Google services during startup: {ce}")
        if 'tts' in locals(): tts.speak("Could not connect to Google services. Calendar features might be unavailable.")
        # calendar_agent might be None or its service uninitialized.
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {e}", exc_info=True)
        print(f"Unexpected error during initialization: {e}")
        if 'tts' in locals(): tts.speak("An critical error occurred during startup. Exiting.")
        return # For other critical errors, exit

    try:
        while True:
            # ... (input method choice logic remains the same) ...
            command_input_method = ""
            user_command_after_choice = None
            while command_input_method not in ['s', 't']:
                try:
                    raw_input_str = input("Choose input method: Speak (s) or Type (t), then press Enter: ").strip()
                    if not raw_input_str:
                        print("No input received. Please enter 's' or 't'.")
                        continue
                    choice_char = raw_input_str[0].lower()
                    if choice_char in ['s', 't']:
                        command_input_method = choice_char
                        if len(raw_input_str) > 1 and command_input_method == 't':
                            user_command_after_choice = raw_input_str[1:].strip()
                            if not user_command_after_choice: user_command_after_choice = None
                    else:
                        print("Invalid choice. Please enter 's' or 't'.")
                except EOFError:
                    logger.info("EOF received, exiting.")
                    if 'tts' in locals(): tts.speak("Exiting.")
                    return
                except IndexError:
                     print("No input received. Please enter 's' or 't'.")

            text_command = None
            if command_input_method == "s":
                # ... (speech input logic) ...
                logger.info("Listening for voice command...")
                if 'tts' in locals(): tts.speak("Listening...")
                text_command = recognizer.listen() if 'recognizer' in locals() else None
                if text_command: logger.info(f"Voice command received: {text_command}")
                else:
                    logger.info("No voice command detected.")
                    if 'tts' in locals(): tts.speak("I didn't catch that.")
                    continue
            else: # command_input_method == "t"
                # ... (text input logic) ...
                if user_command_after_choice: text_command = user_command_after_choice
                else:
                    try: text_command = input("Type command: ")
                    except EOFError: text_command = "exit jarvis"
                    except KeyboardInterrupt:
                        logger.info("Keyboard interrupt, exiting.")
                        if 'tts' in locals(): tts.speak("Exiting.")
                        return

            if text_command:
                if 'tts' in locals(): tts.speak(f"Processing: {text_command}")
                response_message = process_command_text(
                    text_command, parser, os_agent, app_agent,
                    media_agent, web_agent, calendar_agent # Pass calendar_agent
                )
                if response_message == "Goodbye!":
                    logger.info("Exit command processed.")
                    if 'tts' in locals(): tts.speak(response_message)
                    break
                logger.info(f"Response to user: {response_message}")
                if 'tts' in locals(): tts.speak(response_message)
            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("User interrupted main loop. Shutting down.")
        if 'tts' in locals(): tts.speak("Shutting down.")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        if 'tts' in locals(): tts.speak("A critical error occurred. Check logs.")
    finally:
        logger.info("J.A.R.V.I.S. Assistant CLI shutting down.")

if __name__ == "__main__":
    main_loop()
