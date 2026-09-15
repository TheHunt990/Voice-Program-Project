import json
import os
import threading
import pyaudio
from vosk import Model, KaldiRecognizer

# Default location the README tells the user to unzip a model into
DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "model")
SAMPLE_RATE = 16000
CHUNK_SIZE = 4000


class VoiceListener:
    def __init__(self, on_text, on_partial=None, on_status=None, on_error=None, model_path=DEFAULT_MODEL_PATH):
        self.on_text = on_text
        self.on_partial = on_partial
        self.on_status = on_status
        self.on_error = on_error

        model_path = os.path.abspath(model_path)
        try:
            self.model = Model(model_path)
        except Exception as e:
            raise RuntimeError(
                f"No Vosk model found at '{model_path}'.\n"
                "Download one from https://alphacephei.com/vosk/models "
                "(vosk-model-small-en-us-0.15 is a good small starting "
                "point) and unzip it so its contents sit directly in "
                "that 'model' folder."
            ) from e

        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.audio = pyaudio.PyAudio()

        self._running = False
        self._thread = None
        self._stream = None

    def start(self):
        # Begins continuous background listening
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def _listen_loop(self):
        try:
            self._stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )
        except OSError as e:
            self._running = False
            if self.on_error:
                self.on_error(f"Microphone error: {e}")
            return

        if self.on_status:
            self.on_status("listening...")

        try:
            while self._running:
                data = self._stream.read(CHUNK_SIZE, exception_on_overflow=False)
                if not data:
                    continue

                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text:
                        self.on_text(text)
                else:
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get("partial", "").strip()
                    if partial_text and self.on_partial:
                        self.on_partial(partial_text)
        except Exception as e:
            if self.on_error:
                self.on_error(f"Listening error: {e}")
        finally:
            self._stream.stop_stream()
            self._stream.close()

    def stop(self):
        # Stops the background listening
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.5)
        self.audio.terminate()
        if self.on_status:
            self.on_status("stopped")