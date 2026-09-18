import pyttsx3
import threading

class VoiceSpeaker:
    def __init__(self, rate = 175):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self._lock = threading.Lock()

    def say(self, text):
       
        def _speak():
            with self._lock:
                self.engine.say(text)
                self.engine.runAndWait()

        threading.Thread(target = _speak, daemon = True).start()

        
