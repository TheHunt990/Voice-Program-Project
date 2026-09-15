import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from core.listener import VoiceListener
from core.speaker import VoiceSpeaker

# Voice phrases that trigger each mode
SECOND_BRAIN_PHRASES = ["second brain", "notes mode", "task mode"]
ADVENTURE_PHRASES = ["choose your adventure", "adventure mode", "story mode", "adventure"]

# Path to the unzipped Vosk model folder
MODEL_PATH = Path(__file__).parent / "vosk-model-small-en-us-0.15"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Voice Control Hub")
        self.geometry("640x520")
        self.minsize(560, 460)
        self.event_queue = queue.Queue()
        self.speaker = VoiceSpeaker()
        self.listener = VoiceListener(
            model_path=str(MODEL_PATH),
            on_text=self._queue_text,
            on_partial=self._queue_partial,
            on_status=self._queue_status,
            on_error=self._queue_error,
        )
        self._live_line_active = False
        self._live_line_start = None
        self._build_ui()
        self._set_status("starting up...", level="starting")
        self._start_listening()
        self.after(50, self._poll_queue)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # UI for program
    def _build_ui(self):
        title = ttk.Label(self, text="Voice Control Hub", font=("Segoe UI", 20, "bold"))
        title.pack(pady=(18, 4))

        subtitle = ttk.Label(self, text='Say "Second Brain or "Choose your adventure" - or click a button below', font=("Segoe UI", 10), foreground="#555555")
        subtitle.pack(pady=(0, 12))
        subtitle2 = ttk.Label(self, text='You can also say "notes mode, task mode, adventure mode, adventure and story mode"', font=("Segoe UI", 10), foreground="#555555")
        subtitle2.pack(pady=(0, 12))

        # Status dynamic where color of dot changes based on status of the program (starting up, listening, error, stopped)
        status_frame = ttk.Frame(self)
        status_frame.pack(pady=(0, 10))

        self.status_icon = tk.Label(status_frame, text="●", font=("Segoe UI", 12), fg="#e6b800")  # yellow to start
        self.status_icon.pack(side="left", padx=(0, 6))

        self.status_label = ttk.Label(status_frame, text="Status: starting up...", font=("Segoe UI", 10, "italic"))
        self.status_label.pack(side="left")

        # Mode buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=(0, 16))

        self.second_brain_mode_btn = ttk.Button(button_frame, text="🧠 Second Brain", command=self.launch_second_brain_mode, width=24)  # just copied and pasted emojis from emojidb.org
        self.second_brain_mode_btn.grid(row=0, column=0, padx=10, ipady=14)

        self.adventure_mode_btn = ttk.Button(button_frame, text="🧭 Choose your adventure", command=self.launch_adventure_mode, width=24)
        self.adventure_mode_btn.grid(row=0, column=1, padx=10, ipady=14)

        # Live transcript box (mainly to provide a visual of the speech recognition and what the user is saying)
        transcript_label = ttk.Label(self, text="Live transcript:", font=("Segoe UI", 10, "bold"))
        transcript_label.pack(anchor="w", padx=16)

        transcript_frame = ttk.Frame(self)
        transcript_frame.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        self.transcript_box = tk.Text(transcript_frame, wrap="word", font=("Consolas", 11), state="disabled")
        scrollbar = ttk.Scrollbar(transcript_frame, command=self.transcript_box.yview)
        self.transcript_box.configure(yscrollcommand=scrollbar.set)
        self.transcript_box.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _set_status(self, text, level="info"):
        colors = {"starting": "#e6b800", "listening": "#00cc44", "error": "#ff3300", "stopped": "#999999"}
        self.status_icon.config(fg=colors.get(level, "#999999"))
        self.status_label.config(text=f"Status: {text}")

    # voice
    def _start_listening(self):
        threading.Thread(target=self.listener.start, daemon=True).start()

    def _queue_text(self, text):
        self.event_queue.put(("text", text))

    def _queue_partial(self, text):
        self.event_queue.put(("partial", text))

    def _queue_status(self, status):
        self.event_queue.put(("status", status))

    def _queue_error(self, message):
        self.event_queue.put(("error", message))

    def _poll_queue(self):
        """Runs on the main thread every 50ms — the only place GUI
        widgets get touched, which keeps Tkinter happy."""
        try:
            while True:
                kind, payload = self.event_queue.get_nowait()
                if kind == "partial":
                    self._update_partial_line(payload)
                elif kind == "text":
                    self._commit_final_line(payload)
                    self._check_voice_commands(payload)
                elif kind == "status":
                    level = "listening" if payload == "listening..." else "starting"
                    self._set_status(payload, level=level)
                elif kind == "error":
                    self._set_status(payload, level="error")
                    self._append_transcript(f"[{payload}]")
        except queue.Empty:
            pass
        finally:
            self.after(50, self._poll_queue)

    def _append_transcript(self, line):
        """Add a plain, already-finished line (errors, mode-launch
        notices) — not part of the live partial-line mechanism."""
        self.transcript_box.configure(state="normal")
        self.transcript_box.insert("end", line + "\n")
        self.transcript_box.see("end")
        self.transcript_box.configure(state="disabled")

    def _update_partial_line(self, text):
        """Called repeatedly while Vosk is still guessing mid-phrase.
        Rewrites the same line in place instead of appending a new one
        each time, which is what makes the transcript feel live."""
        self.transcript_box.configure(state="normal")
        if not self._live_line_active:
            self._live_line_start = self.transcript_box.index("end-1c")
            self._live_line_active = True
        else:
            self.transcript_box.delete(self._live_line_start, "end-1c")
        self.transcript_box.insert(self._live_line_start, text)
        self.transcript_box.see("end")
        self.transcript_box.configure(state="disabled")

    def _commit_final_line(self, text):
        """Called once Vosk decides the phrase is complete. Replaces
        whatever partial guess was on screen with the final text and
        closes off the line with a newline."""
        self.transcript_box.configure(state="normal")
        if self._live_line_active:
            self.transcript_box.delete(self._live_line_start, "end-1c")
            self.transcript_box.insert(self._live_line_start, text + "\n")
            self._live_line_active = False
            self._live_line_start = None
        else:
            self.transcript_box.insert("end", text + "\n")
        self.transcript_box.see("end")
        self.transcript_box.configure(state="disabled")

    def _check_voice_commands(self, text):
        lowered = text.lower()
        if any(trigger in lowered for trigger in SECOND_BRAIN_PHRASES):
            self.launch_second_brain_mode()
        elif any(trigger in lowered for trigger in ADVENTURE_PHRASES):
            self.launch_adventure_mode()

    # Mode launching
    def launch_second_brain_mode(self):
        self._append_transcript("Launching Second Brain mode...")
        print("Launching Second Brain mode...")

    def launch_adventure_mode(self):
        self._append_transcript("Launching Choose your adventure mode...")
        print("Launching Choose your adventure mode...")

    # Shutdown
    def _on_close(self):
        self.listener.stop()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()