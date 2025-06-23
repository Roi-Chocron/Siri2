# Handles voice output
import pyttsx3

class TextToSpeech:
    def __init__(self):
        self.engine = pyttsx3.init()
        # Optional: Adjust properties like rate, volume
        # self.engine.setProperty('rate', 150)
        # self.engine.setProperty('volume', 0.9)
        voices = self.engine.getProperty('voices')
        # You might want to select a specific voice if needed
        # For example, to select a female voice if available
        # self.engine.setProperty('voice', voices[1].id) # Index might vary

    def speak(self, text: str):
        """
        Speaks the given text.
        """
        if not text:
            print("TTS: No text to speak.")
            return
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Error in TTS: {e}")

if __name__ == '__main__':
    tts = TextToSpeech()
    tts.speak("Hello, I am your virtual assistant. How can I help you today?")
    tts.speak("This is a test of the text to speech system.")
