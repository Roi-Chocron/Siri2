# Handles voice input
import speech_recognition as sr

class SpeechRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        # Adjust for ambient noise once at the beginning
        # with self.microphone as source:
        #     self.recognizer.adjust_for_ambient_noise(source)
        # print("Speech recognizer initialized and calibrated for ambient noise.")


    def listen(self) -> str | None:
        """
        Listens for a command from the user via microphone.
        Returns the recognized text or None if recognition fails.
        """
        with self.microphone as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5) # Re-calibrate quickly
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                print("No speech detected within timeout.")
                return None

        try:
            print("Recognizing...")
            # Using Google Web Speech API by default with SpeechRecognition
            # This requires internet access.
            # For offline, CMU Sphinx (PocketSphinx) can be configured.
            command = self.recognizer.recognize_google(audio)
            print(f"Recognized: {command}")
            return command.lower()
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during speech recognition: {e}")
            return None

if __name__ == '__main__':
    recognizer = SpeechRecognizer()
    while True:
        command = recognizer.listen()
        if command:
            if "exit" in command or "quit" in command:
                print("Exiting listener test.")
                break
            print(f"You said: {command}")
        else:
            print("No command recognized or error occurred.")
