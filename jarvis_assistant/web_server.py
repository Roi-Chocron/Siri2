from flask import Flask, request, jsonify, render_template
import sys
import os

# Add the parent directory to sys.path to allow imports from jarvis_assistant
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jarvis_assistant.main import process_command_text # We'll define this function later in main.py
from jarvis_assistant.core.text_to_speech import TextToSpeech # For initial greeting perhaps, or if UI needs to speak
from jarvis_assistant.utils.logger import get_logger

app = Flask(__name__)
logger = get_logger("JARVIS_WebServer")
# tts = TextToSpeech() # Initialize TTS if needed for web responses; typically UI handles speech

# A global variable to hold initialized components from main.py
# This avoids re-initializing them on every request.
jarvis_components = {}

def initialize_jarvis_core():
    """
    Initializes the core components of JARVIS needed for command processing.
    This function will be called once when the server starts.
    It should replicate the necessary parts of main_loop() initialization.
    """
    from jarvis_assistant.core.command_parser import CommandParser
    from jarvis_assistant.modules.os_interaction import OSInteraction
    from jarvis_assistant.modules.app_manager import AppManager
    from jarvis_assistant.modules.media_controller import MediaController
    from jarvis_assistant.modules.web_automator import WebAutomator
    from jarvis_assistant.config import GEMINI_API_KEY

    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        logger.error("Gemini API key not configured in jarvis_assistant/config.py.")
        # This is a server, so we can't easily prompt the user.
        # The UI should ideally show an error if the backend fails to start.
        raise RuntimeError("Gemini API key not configured.")

    try:
        jarvis_components['parser'] = CommandParser()
        jarvis_components['os_agent'] = OSInteraction()
        jarvis_components['app_agent'] = AppManager()
        jarvis_components['media_agent'] = MediaController()
        jarvis_components['web_agent'] = WebAutomator()
        # SpeechRecognizer and TextToSpeech are not directly used by the web command processing logic,
        # as input comes via HTTP and output goes back as text/JSON.
        # TTS might be used by the UI with browser APIs.
        logger.info("JARVIS core components initialized for web server.")
    except Exception as e:
        logger.error(f"Error initializing JARVIS components: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize JARVIS components: {e}")

@app.route('/')
def index():
    """Serves the main HTML page for the web UI."""
    return render_template('index.html')

@app.route('/command', methods=['POST'])
def handle_command():
    data = request.get_json()
    if not data or 'command' not in data:
        logger.warning("Received invalid command request: no data or 'command' field missing.")
        return jsonify({"error": "Invalid request. 'command' field is required."}), 400

    command_text = data['command']
    logger.info(f"Web server received command: {command_text}")

    if not jarvis_components:
        logger.error("JARVIS components not initialized. This should not happen.")
        return jsonify({"response": "Error: Assistant components not ready."}), 500

    # Call the refactored command processing logic
    # This function will need access to the initialized components.
    response_message = process_command_text(
        command_text,
        jarvis_components['parser'],
        jarvis_components['os_agent'],
        jarvis_components['app_agent'],
        jarvis_components['media_agent'],
        jarvis_components['web_agent']
        # No TTS or recognizer needed here for web processing
    )

    logger.info(f"Sending response for command '{command_text}': {response_message}")
    return jsonify({"response": response_message})

def run_server():
    try:
        initialize_jarvis_core()
        logger.info("Starting Flask web server for J.A.R.V.I.S...")
        print("Flask server starting...")
        print("J.A.R.V.I.S. web interface will be available at http://127.0.0.1:5000/")
        print("Press CTRL+C to stop the server.")
        # tts.speak("J.A.R.V.I.S. web interface is now active.") # Optional, if server has audio out
        app.run(host='0.0.0.0', port=5000, debug=False) # debug=False for production/safer runs
    except RuntimeError as e:
        logger.error(f"Could not start web server: {e}")
        print(f"ERROR: Could not start J.A.R.V.I.S. web server: {e}")
        # Optionally, try to speak this error if TTS is available and it's a critical startup failure.
        # if 'tts' in locals() or 'tts' in globals():
        # tts.speak(f"Critical error. Web server could not start. Check logs.")
    except Exception as e:
        logger.error(f"An unexpected error occurred trying to start the web server: {e}", exc_info=True)


if __name__ == '__main__':
    run_server()
