import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Voice Control Hub")  
        self.geometry("640x520")
        self.minsize(560, 460)
        self._build_ui()
        self._set_status("starting up...", level = "starting")
        self.after(2000, lambda: self._set_status("listening...", level = "listening")) # demo only remove once fully worked on listener is complete

# UI for program
    def _build_ui(self):
        title = ttk.Label(self, text= "Voice Control Hub", font = ("Segoe UI", 20, "bold"))
        title.pack(pady = (18, 4))

        subtitle = ttk.Label(self, text = 'Say "Second Brain or "Choose your adventure" - or click a button below', font = ("Segoe UI", 10), foreground = "#555555")
        subtitle.pack(pady = (0, 12))
        subtitle2 = ttk.Label(self, text = 'You can also say "notes mode, task mode, adventure mode, adventure and story mode"', font = ("Segoe UI", 10), foreground = "#555555")
        subtitle2.pack(pady = (0, 12))

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

        self.second_brain_mode_btn = ttk.Button(button_frame, text ="🧠 Second Brain", command = self.launch_second_brain_mode, width = 24) # just copied and pasted emojis from emojidb.org
        self.second_brain_mode_btn.grid(row = 0, column = 0, padx = 10, ipady = 14)

        self.adventure_mode_btn = ttk.Button(button_frame, text = "🧭 Choose your adventure", command = self.launch_adventure_mode, width = 24)
        self.adventure_mode_btn.grid(row = 0, column = 1, padx = 10, ipady = 14)

    # Live transcript box (mainly to provide a visual of the speech recognition and what the user is saying)
        transcript_label = ttk.Label(self, text = "Live transcript:", font = ("Segoe UI", 10, "bold"))
        transcript_label.pack(anchor="w", padx=16)

        transcript_frame = ttk.Frame(self)
        transcript_frame.pack(fill = "both", expand=True, padx = 16, pady = (4, 16))

        self.transcript_box = tk.Text(transcript_frame, wrap="word", font = ("Consolas", 11), state="disabled")
        scrollbar = ttk.Scrollbar(transcript_frame, command = self.transcript_box.yview)
        self.transcript_box.configure(yscrollcommand = scrollbar.set)
        self.transcript_box.pack(side = "left", fill = "both", expand =True)
        scrollbar.pack(side = "right", fill = "y")

    # Mode launching
    def launch_second_brain_mode(self):
        print("Launching Second Brain mode...")

    def launch_adventure_mode(self):
        print("Launching Choose your adventure mode...")

    def _set_status(self, text, level="info"):
         colors = {"starting": "#e6b800", "listening": "#00cc44", "error": "#ff3300", "stopped": "#999999"}
         self.status_icon.config(fg=colors.get(level, "#999999"))
         self.status_label.config(text=f"Status: {text}")                    

if __name__ == "__main__":
        app = App()
        app.mainloop()
