# Main application entry point
import time
from jarvis_assistant.core.speech_recognizer import SpeechRecognizer
from jarvis_assistant.core.text_to_speech import TextToSpeech
from jarvis_assistant.core.command_parser import CommandParser
from jarvis_assistant.modules.os_interaction import OSInteraction
from jarvis_assistant.modules.app_manager import AppManager
from jarvis_assistant.modules.media_controller import MediaController
from jarvis_assistant.modules.web_automator import WebAutomator # Import WebAutomator
from jarvis_assistant.utils.logger import get_logger
from jarvis_assistant.config import GEMINI_API_KEY
import os

logger = get_logger("JARVIS_Main")

def handle_os_interaction(os_agent: OSInteraction, intent: str, entities: dict) -> str:
    """Handles OS interaction based on intent and entities."""
    response_message = "Sorry, I couldn't perform that OS action." # Default error
    success = False

    if intent == "create_text_file":
        filepath = entities.get("filepath")
        content = entities.get("content", "")
        if filepath:
            # Make paths relative to user's home directory if not absolute
            if not os.path.isabs(filepath):
                filepath = os.path.expanduser(os.path.join("~", filepath))
            success, response_message = os_agent.create_text_file(filepath, content)
        else:
            response_message = "I need a filepath to create a text file."

    elif intent == "create_directory":
        dir_path = entities.get("dir_path")
        if dir_path:
            if not os.path.isabs(dir_path):
                dir_path = os.path.expanduser(os.path.join("~", dir_path))
            success, response_message = os_agent.create_directory(dir_path)
        else:
            response_message = "I need a directory path to create a directory."

    elif intent == "delete_path":
        path_to_delete = entities.get("path")
        if path_to_delete:
            if not os.path.isabs(path_to_delete):
                path_to_delete = os.path.expanduser(os.path.join("~", path_to_delete))
            success, response_message = os_agent.delete_path(path_to_delete)
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
            success, response_message = os_agent.move_path(source_path, destination_path)
        else:
            response_message = "I need both a source and a destination path to move."

    elif intent == "list_directory_contents":
        dir_path = entities.get("dir_path", "~") # Default to home if not specified
        if not os.path.isabs(dir_path) and dir_path != "~":
             dir_path = os.path.expanduser(os.path.join("~", dir_path))
        elif dir_path == "~":
            dir_path = os.path.expanduser("~")

        success, result = os_agent.list_directory_contents(dir_path)
        if success:
            if isinstance(result, list):
                response_message = f"Contents of {dir_path}:\n" + "\n".join(result)
                if not result: response_message = f"The directory {dir_path} is empty."
            else: # String message (e.g. dir not found, or is empty string)
                response_message = result
        else:
            response_message = result # Error message from os_agent

    elif intent == "execute_command":
        command_str = entities.get("command_str")
        shell_type = entities.get("shell_type")
        if os.name == 'nt' and not shell_type:
            shell_type = "cmd"
        elif os.name != 'nt' and not shell_type:
            shell_type = "sh"

        if command_str:
            # SECURITY WARNING: Executing arbitrary commands is risky.
            # Consider a more restrictive approach for production.
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
                success, response_message = os_agent.set_brightness(level)
            except ValueError:
                response_message = "Brightness level must be an integer."
        else:
            response_message = "I need a brightness level."

    elif intent == "set_volume":
        level = entities.get("level")
        if level is not None:
            try:
                level = float(level)
                success, response_message = os_agent.set_volume(level)
            except ValueError:
                response_message = "Volume level must be a number (e.g., 0.5 for 50%)."
        else:
            response_message = "I need a volume level."
    else:
        response_message = f"OS interaction for intent '{intent}' is not yet implemented."

    return response_message


def main_loop():
    logger.info("J.A.R.V.I.S. Assistant Initializing...")

    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        logger.error("Gemini API key not configured. Please set it in jarvis_assistant/config.py and restart.")
        print("CRITICAL ERROR: Gemini API key not configured. Please set it in jarvis_assistant/config.py and restart.")
        return

    try:
        recognizer = SpeechRecognizer()
        tts = TextToSpeech()
        parser = CommandParser()
        os_agent = OSInteraction()
        app_agent = AppManager()
        media_agent = MediaController()
        web_agent = WebAutomator() # Initialize WebAutomator
        logger.info("Core components initialized.")
        tts.speak("J.A.R.V.I.S. online and ready.")
    except ValueError as ve:
        logger.error(f"Initialization error: {ve}")
        print(f"Initialization error: {ve}")
        return
    except Exception as e:
        logger.error(f"Unexpected error during initialization: {e}")
        print(f"Unexpected error during initialization: {e}")
        return

    try:
        while True:
            logger.info("Starting new listening cycle.")
            # Allow for text input as well for debugging or environments without mic
            # command_input_method = "voice" # or "text"
            # if command_input_method == "voice":
            text_command = recognizer.listen()
            # else:
            #     text_command = input("Enter command: ")

            if text_command:
                logger.info(f"Recognized command: {text_command}")
                tts.speak(f"Processing: {text_command}")

                if "exit jarvis" in text_command or "quit jarvis" in text_command:
                    logger.info("Exit command received. Shutting down.")
                    tts.speak("Goodbye!")
                    break

                # Get parsed command/action from LLM
                parsed_action = parser.parse_command(text_command)
                logger.info(f"LLM parsed action: {parsed_action}")

                intent = parsed_action.get("intent", "unknown")
                entities = parsed_action.get("entities", {})

                response_message = ""

                if intent == "exit":
                    logger.info("Exit intent recognized by LLM. Shutting down.")
                    response_message = "Goodbye!"
                    tts.speak(response_message)
                    break

                # OS Interaction Intents
                elif intent in [
                    "create_text_file", "create_directory", "delete_path",
                    "move_path", "list_directory_contents", "execute_command",
                    "set_brightness", "set_volume"
                ]:
                    response_message = handle_os_interaction(os_agent, intent, entities)

                # Placeholder for other intent categories (App, Web, Media)
                elif intent == "open_app":
                    app_name = entities.get("app_name")
                    if app_name:
                        if app_agent.open_app(app_name):
                            response_message = f"Opening {app_name}."
                        else:
                            response_message = f"Sorry, I couldn't open {app_name}."
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
                    summarize = entities.get("summarize", False) # Default to False
                    if query:
                        search_result = web_agent.search_info(query, summarize)
                        if summarize:
                            response_message = f"Here's what I found about {query}: {search_result}"
                        else:
                            response_message = f"I've opened a browser tab with search results for {query}."
                            # search_result here is the URL, could also say "You can find it at {search_result}"
                    else:
                        response_message = "What would you like me to search for?"
                elif intent == "media_play":
                    player_name = entities.get("player_name", "default")
                    track_or_playlist = entities.get("track_or_playlist")
                    success, msg = media_agent.play(player_name, track_or_playlist)
                    response_message = msg
                elif intent == "media_pause":
                    player_name = entities.get("player_name", "default")
                    success, msg = media_agent.pause(player_name)
                    response_message = msg
                elif intent == "media_skip":
                    player_name = entities.get("player_name", "default")
                    success, msg = media_agent.skip_track(player_name)
                    response_message = msg
                elif intent == "media_previous":
                    player_name = entities.get("player_name", "default")
                    success, msg = media_agent.previous_track(player_name)
                    response_message = msg
                elif intent == "general_query":
                    # For general queries, we might just pass the query text back to the LLM
                    # or handle simple ones like "what time is it?" directly.
                    # For now, just echo what the LLM might say or a generic response.
                    query_text = entities.get("query_text", text_command)
                    # This could be another LLM call for a conversational response
                    response_message = f"Regarding your query: {query_text}... I'm still learning to handle general conversation."
                elif intent == "unknown":
                    response_message = "I'm not sure how to handle that command. Could you try rephrasing?"
                    if "error" in entities: # If LLM itself had an issue producing JSON
                        response_message += f" (Parser error: {entities['error']})"
                else:
                    response_message = f"I understood the intent as '{intent}', but I don't know how to do that yet."

                logger.info(f"Response to user: {response_message}")
                tts.speak(response_message)

            else:
                # logger.info("No command recognized or error in recognition.")
                # tts.speak("Sorry, I didn't catch that. Could you please repeat?")
                # No command, or error already logged by recognizer.listen()
                pass

            time.sleep(0.1) # Small delay to prevent tight looping if mic issues

    except KeyboardInterrupt:
        logger.info("User interrupted the main loop. Shutting down.")
        if 'tts' in locals(): # Check if tts was initialized
            tts.speak("Shutting down due to user request.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
        if 'tts' in locals():
            tts.speak("An critical error occurred. Please check the logs.")
    finally:
        logger.info("J.A.R.V.I.S. Assistant shutting down.")

if __name__ == "__main__":
    main_loop()
