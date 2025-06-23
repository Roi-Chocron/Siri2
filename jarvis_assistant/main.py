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

    if intent == "create_file":
        filepath = entities.get("filepath")
        content = entities.get("content", "")
        file_type = entities.get("file_type", "txt") # Default to txt
        if filepath:
            # Check for attempts to write to root of a drive (e.g., C:\file.txt)
            # os.path.dirname("C:/file.txt") -> C:/
            # os.path.abspath(os.sep) gives the root of the current drive, e.g. C:\
            # A more direct check for "C:/file.txt" style paths:
            path_obj = os.path.normpath(filepath) # Normalize (e.g. C:/file.txt -> C:\file.txt on Win)
            # Check if the parent directory is the root directory.
            # Example: dirname of 'C:\file.txt' is 'C:\'. For 'file.txt' it's ''.
            # If os.path.dirname(path_obj) is 'C:\\' (Windows) or '/' (POSIX)
            # This check is a bit simplistic, as user might not have typed C:/ but C:file.txt
            # A better check is if the path starts with "X:\" or "X:/" and has no further subdirs for the file itself.

            # Let's refine the check for root directory paths.
            # A common problematic pattern is "C:/file.txt" or "/file.txt"
            # os.path.splitdrive("C:/file.txt") -> ('C:', '/file.txt')
            # os.path.splitdrive("/file.txt") -> ('', '/file.txt')
            drive, tail = os.path.splitdrive(path_obj)
            is_root_path_attempt = False
            if drive and tail.startswith(os.sep) and len(tail.strip(os.sep).split(os.sep)) == 1:
                 # e.g. C:\file.txt -> drive='C:', tail='\file.txt'
                 # tail.strip(os.sep) -> 'file.txt'
                 # tail.strip(os.sep).split(os.sep) -> ['file.txt']
                 is_root_path_attempt = True
            elif not drive and path_obj.startswith(os.sep) and len(path_obj.strip(os.sep).split(os.sep)) == 1:
                # e.g. /file.txt (POSIX)
                is_root_path_attempt = True

            if is_root_path_attempt:
                response_message = (
                    f"Creating files directly in the root directory ('{os.path.dirname(path_obj)}') "
                    "is often restricted. Please try specifying a path within your user folders "
                    "(e.g., 'Documents/my_file.txt' or 'my_file.txt' to save in your home directory)."
                )
                # No 'success = False' here, as os_agent.create_file isn't called yet.
            else:
                # Make paths relative to user's home directory if not absolute
                # This logic should only apply if the path is NOT already absolute.
                # The LLM might provide an absolute path like "C:\Users\user\Documents\file.txt"
                # or a relative one like "my_folder/file.txt".
                # If it's like "C:/file.txt", the above check should catch it.
                # If it's like "jarvis_assistant/ttt.txt" as in the log, this should be handled.

                # Original logic for expanding path:
                # if not os.path.isabs(filepath):
                #    filepath = os.path.expanduser(os.path.join("~", filepath))
                # This assumes that a non-absolute path given by the LLM should always be relative to home.
                # This seems reasonable. Let's ensure the original filepath is used for the is_root_path_attempt check.

                # Re-evaluate path expansion:
                # If `filepath` from LLM is like "C:/some/path/file.txt", it's absolute.
                # If `filepath` is "my_docs/file.txt", it's relative.
                # The `os.path.expanduser(os.path.join("~", filepath))` is good for relative paths.

                # Use the original filepath from entities for the root check, then expand if not absolute.
                processed_filepath = filepath
                if not os.path.isabs(processed_filepath):
                    # This will turn "file.txt" into "/Users/username/file.txt"
                    # or "myfolder/file.txt" into "/Users/username/myfolder/file.txt"
                    processed_filepath = os.path.expanduser(os.path.join("~", processed_filepath))

                # Now, `processed_filepath` is absolute.
                # The root check should have been done on the `filepath` as provided by LLM if it was intended as absolute.
                # Or, if the LLM gave "C:/file.txt", `is_root_path_attempt` above handles it.
                # If LLM gave "file.txt", it becomes "~/file.txt", which is fine.

                # The issue arises if LLM gives "C:/file.txt", and we *don't* expand it to home.
                # So, the `is_root_path_attempt` should be on the `filepath` *before* home expansion if it's absolute.
                # And if it's relative, it will be expanded to home, which is usually safe.

                # Let's simplify: if the original filepath from LLM is absolute AND is a root path, warn.
                # Otherwise, if relative, expand to home. If absolute and not root, use as is.

                final_filepath_to_use = filepath
                if os.path.isabs(filepath):
                    # Check if this absolute path is a root attempt
                    drive_abs, tail_abs = os.path.splitdrive(os.path.normpath(filepath))
                    if (drive_abs and tail_abs.startswith(os.sep) and len(tail_abs.strip(os.sep).split(os.sep)) == 1) or \
                       (not drive_abs and filepath.startswith(os.sep) and len(filepath.strip(os.sep).split(os.sep)) == 1):
                        response_message = (
                            f"Creating files directly in a root directory like '{os.path.dirname(os.path.normpath(filepath))}' "
                            "is often restricted due to permissions. Please try a path in your user folders, "
                            "like 'Documents/my_file.txt', or just a filename to save in your home directory."
                        )
                        # success remains False by default
                    else: # Absolute path, not root, use as is
                        success, response_message = os_agent.create_file(final_filepath_to_use, content, file_type)
                else: # Relative path, expand to home
                    final_filepath_to_use = os.path.expanduser(os.path.join("~", filepath))
                    success, response_message = os_agent.create_file(final_filepath_to_use, content, file_type)
        else:
            response_message = "I need a filepath to create a file."

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
            # Default to voice input. Text input can be a fallback or configurable option.
            # For now, we'll set it directly to "voice".
            # A more advanced setup might use a config variable from config.py
            # command_input_method = "voice" # Defaulting to voice

            command_input_method = ""
            user_command_after_choice = None # To store any extraneous input after 's' or 't'
            while command_input_method not in ['s', 't']:
                try:
                    # Prompting in the console, not via TTS, as this is a pre-command setup
                    raw_input_str = input("Choose input method: Speak (s) or Type (t), then press Enter: ").strip()
                    if not raw_input_str: # Empty input
                        print("No input received. Please enter 's' or 't'.")
                        continue

                    choice_char = raw_input_str[0].lower()

                    if choice_char in ['s', 't']:
                        command_input_method = choice_char
                        # Check if there was more text after the choice, only relevant for 't'
                        if len(raw_input_str) > 1 and command_input_method == 't':
                            user_command_after_choice = raw_input_str[1:].strip()
                            if not user_command_after_choice: # e.g. user typed "t "
                                user_command_after_choice = None
                    else:
                        print("Invalid choice. Please enter 's' or 't'.")
                except EOFError:
                    logger.info("EOF received during input mode selection, treating as exit.")
                    tts.speak("Exiting.")
                    return # Exit main_loop
                except IndexError: # Catch if input was empty after strip
                     print("No input received. Please enter 's' or 't'.")


            text_command = None
            if command_input_method == "s": # Speech input
                logger.info("Listening for voice command...")
                tts.speak("Listening...")
                text_command = recognizer.listen()
                if text_command:
                    logger.info(f"Voice command received: {text_command}")
                else:
                    logger.info("No voice command detected or error in recognition.")
                    tts.speak("I didn't catch that. Please try again.")
                    continue # Skip processing if no command heard
            else: # Text input mode (command_input_method == "t")
                if user_command_after_choice:
                    text_command = user_command_after_choice
                    logger.info(f"Using command from initial choice: {text_command}")
                else:
                    try:
                        text_command = input("הקלד פקודה: ") # "Type command: " in Hebrew as per user log
                    except EOFError:
                        logger.info("EOF received, treating as exit command.")
                        text_command = "exit jarvis" # Or handle exit more directly
                    except KeyboardInterrupt:
                        logger.info("Keyboard interrupt during text input, treating as exit.")
                        tts.speak("Exiting.")
                        return # Exit main_loop

            if text_command: # Proceed only if a command was actually received
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
                    "create_file", "create_directory", "delete_path", # Updated create_text_file to create_file
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
                            if os.name == 'nt':
                                if app_name.lower() == "microsoft store":
                                    response_message = "Opening the Microsoft Store programmatically is complex. You might need to open it manually or set up a custom shortcut in USER_APP_PATHS in config.py."
                                else:
                                    response_message = (
                                        f"Sorry, I couldn't open '{app_name}'. "
                                        "Please ensure it's installed and the name is correct. "
                                        "If it's a Microsoft Store app or in a non-standard location, "
                                        "you may need to add its specific launch command or full path "
                                        "to USER_APP_PATHS in the jarvis_assistant/config.py file. "
                                        "For Store apps, this might involve an 'explorer.exe shell:AppsFolder\\...' command."
                                    )
                            else: # Non-Windows OS
                                response_message = (
                                    f"Sorry, I couldn't open '{app_name}'. "
                                    "Please ensure it's installed and the name is correct, or add its path "
                                    "to USER_APP_PATHS in the config.py file."
                                )
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
                    query_text_lower = query_text.lower()
                    if "which apps can you open" in query_text_lower or "what apps can you open" in query_text_lower:
                        known_apps = list(app_agent.app_map.keys())
                        response_message = (
                            "I can try to open applications I know by default, like Notepad, Calculator, Chrome, Firefox, and a generic 'browser'. "
                            f"Currently, my full list of recognized app names includes: {', '.join(known_apps)}. "
                            "You can also teach me new ones by adding their full path to USER_APP_PATHS in the config.py file. "
                            "What app would you like to open?"
                        )
                    elif "can you speak" in query_text_lower and "hebrew" in query_text_lower:
                        response_message = "I understand commands in English, and my responses are currently in English. Support for speaking other languages like Hebrew is not yet implemented."
                    else:
                        response_message = f"Regarding your query: {query_text}... I'm still learning to handle general conversation."
                elif intent == "summarize_text":
                    filepath = entities.get("filepath")
                    source_url = entities.get("source_url")
                    text_to_summarize = entities.get("text_to_summarize")

                    if filepath:
                        # Resolve path relative to home if not absolute
                        if not os.path.isabs(filepath):
                            filepath = os.path.expanduser(os.path.join("~", filepath))

                        success_read, content_or_error = os_agent.read_file_content(filepath)
                        if success_read:
                            # For now, just present a snippet as "reading"
                            # TTS might struggle with very long content.
                            snippet = content_or_error[:500] # Read first 500 chars
                            response_message = f"Here's the beginning of the file '{os.path.basename(filepath)}':\n{snippet}"
                            if len(content_or_error) > 500:
                                response_message += "\n\n(The file is longer, I've read the first part.)"
                        else:
                            response_message = content_or_error # This will be the error message from read_file_content
                    elif source_url:
                        # This would be where web_agent.summarize_url(source_url) or similar is called
                        response_message = f"I would summarize {source_url}, but web page summarization needs to be fully connected."
                        # Placeholder: content = web_agent.fetch_page_content(source_url)
                        # if content: response_message = web_agent.summarize_text_content(content) else: ...
                    elif text_to_summarize:
                        # This would be web_agent.summarize_text_content(text_to_summarize)
                        response_message = "I would summarize the text you provided, but text summarization needs to be fully connected."
                    else:
                        response_message = "I need a file path, a URL, or some text to summarize."

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
