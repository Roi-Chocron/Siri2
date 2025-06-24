from flask import Flask, request, jsonify, render_template
import sys
import os

# Add the parent directory to sys.path to allow imports from jarvis_assistant
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jarvis_assistant.main import process_command_text
# from jarvis_assistant.core.text_to_speech import TextToSpeech # Not used in web_server
from jarvis_assistant.utils.logger import get_logger
from jarvis_assistant.config import GEMINI_API_KEY

# Import all necessary modules for initialization
from jarvis_assistant.core.command_parser import CommandParser
from jarvis_assistant.modules.os_interaction import OSInteraction
from jarvis_assistant.modules.app_manager import AppManager
from jarvis_assistant.modules.media_controller import MediaController
from jarvis_assistant.modules.web_automator import WebAutomator
from jarvis_assistant.modules.google_calendar_manager import GoogleCalendarManager

app = Flask(__name__)
logger = get_logger("JARVIS_WebServer")

jarvis_components = {}

def initialize_jarvis_core():
    """
    Initializes the core components of JARVIS needed for command processing.
    This function will be called once when the server starts.
    """
    global jarvis_components # Ensure we're modifying the global dict

    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        logger.error("Gemini API key not configured in jarvis_assistant/config.py.")
        raise RuntimeError("Gemini API key not configured.")

    try:
        jarvis_components['parser'] = CommandParser()
        jarvis_components['os_agent'] = OSInteraction()
        jarvis_components['app_agent'] = AppManager()
        jarvis_components['media_agent'] = MediaController()
        jarvis_components['web_agent'] = WebAutomator()

        # Initialize Calendar Manager
        # This might trigger OAuth flow via console if tokens are not found/valid
        # For a web server, this console interaction during startup is problematic.
        # The GoogleAuthManager needs to gracefully handle this or we need a separate setup step.
        # For now, we'll proceed, but this is a UX concern for server startup.
        # If client_secret.json is missing, GoogleCalendarManager() will raise FileNotFoundError.
        # If auth fails and requires browser, run_local_server in GoogleAuthManager will print to console.
        try:
            jarvis_components['calendar_agent'] = GoogleCalendarManager(read_only=False)
            logger.info("GoogleCalendarManager initialized successfully.")
        except FileNotFoundError as fnf:
            logger.error(f"Failed to initialize GoogleCalendarManager: {fnf}. client_secret.json might be missing.")
            jarvis_components['calendar_agent'] = None # Allow server to run, but calendar features will fail
            # We could raise RuntimeError here to prevent server startup without full functionality
            # raise RuntimeError(f"Failed to initialize GoogleCalendarManager: {fnf}")
        except ConnectionError as ce: # Catch auth errors from GoogleAuthManager
            logger.error(f"Failed to initialize GoogleCalendarManager due to connection/auth error: {ce}")
            jarvis_components['calendar_agent'] = None
            # raise RuntimeError(f"Failed to initialize GoogleCalendarManager: {ce}")
        except Exception as e_cal: # Catch any other calendar init error
            logger.error(f"Unexpected error initializing GoogleCalendarManager: {e_cal}", exc_info=True)
            jarvis_components['calendar_agent'] = None
            # raise RuntimeError(f"Unexpected error initializing GoogleCalendarManager: {e_cal}")


        logger.info("JARVIS core components initialized for web server.")
        if jarvis_components.get('calendar_agent') is None:
            logger.warning("Calendar features will be unavailable due to initialization issues.")
            # Optionally, inform the user on the web UI itself if possible, or just log.

    except Exception as e: # Catch errors from other component initializations
        logger.error(f"Error initializing JARVIS components: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize JARVIS components: {e}")

@app.route('/')
def index():
    """Serves the main HTML page for the web UI."""
    # Check if calendar agent failed to init and pass this info to template
    calendar_error_message = None
    if 'calendar_agent' not in jarvis_components or jarvis_components['calendar_agent'] is None:
        if 'calendar_init_error' in jarvis_components: # Store a specific error message if available
             calendar_error_message = jarvis_components['calendar_init_error']
        else:
            calendar_error_message = "Google Calendar integration is currently unavailable. Please check server logs and Google API setup."

    # A simple way to notify on UI: pass a variable to template.
    # index.html would need to be modified to display this.
    # For now, we'll rely on command responses indicating failure.
    return render_template('index.html')

@app.route('/command', methods=['POST'])
def handle_command():
    data = request.get_json()
    if not data or 'command' not in data:
        logger.warning("Received invalid command request: no data or 'command' field missing.")
        return jsonify({"error": "Invalid request. 'command' field is required."}), 400

    command_text = data['command']
    logger.info(f"Web server received command: {command_text}")

    if not jarvis_components.get('parser'): # Check if core components are even there
        logger.error("JARVIS components not properly initialized.")
        return jsonify({"response": "Error: Assistant components not ready."}), 500

    # Ensure all required components are passed to process_command_text
    response_message = process_command_text(
        command_text,
        jarvis_components['parser'],
        jarvis_components['os_agent'],
        jarvis_components['app_agent'],
        jarvis_components['media_agent'],
        jarvis_components['web_agent'],
        jarvis_components.get('calendar_agent') # Pass calendar_agent, could be None
    )

    logger.info(f"Sending response for command '{command_text}': {response_message}")
    return jsonify({"response": response_message})

def run_server():
    try:
        initialize_jarvis_core()
        logger.info("Starting Flask web server for J.A.R.V.I.S...")
        print("Flask server starting...")
        if jarvis_components.get('calendar_agent') is None:
             print("WARNING: Google Calendar features may be unavailable. Check logs for details (e.g., client_secret.json setup, API auth).")
        print("J.A.R.V.I.S. web interface will be available at http://127.0.0.1:5000/")
        print("Press CTRL+C to stop the server.")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except RuntimeError as e: # Catch errors from initialize_jarvis_core
        logger.error(f"Could not start web server: {e}")
        print(f"ERROR: Could not start J.A.R.V.I.S. web server: {e}")
        print("This might be due to missing API keys or critical component failures.")
    except Exception as e: # Catch other unexpected errors like port in use
        logger.error(f"An unexpected error occurred trying to start the web server: {e}", exc_info=True)
        print(f"FATAL: An unexpected error occurred: {e}")

if __name__ == '__main__':
    run_server()
