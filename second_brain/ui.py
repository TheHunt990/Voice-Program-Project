# Voice commands here:
"""
add note <text>  -> saves a note
add event <text> -> saves an event on the selected day
next month  -> calendar foward
last month/previous  -> calender back
today  -> jump back to today
go back/main menu  -> close and return to main hub
"""

import calendar
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import ttk

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

class SecondBrainWindow(tk.Toplevel):
    def __init__(self, parent, speaker=None, on_close=None):
        super().__init__(parent)
        self.title("Second Brain")
        self.geometry("900x600")
        self.minsize(820, 560)

        self.speaker = speaker
        self._on_close_callback = on_close

        # In-memory storage for now — notes/events vanish on close until
        # storage.py gets wired in.
        self.notes = []
        self.events = {}
        self._next_note_id = 1
        self._next_event_id = 1

        today = date.today()
        self.selected_date = today
        self.view_year = today.year
        self.view_month = today.month
        self._build_ui()
        self._refresh_calendar()
        self._refresh_events()
        self._refresh_notes()

    # UI
    def _build_ui(self):
        # header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(14, 6))
        ttk.Label(header, text="🧠 Second Brain", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(header, text="← Back to hub", command=self.close).pack(side="right")

        self.heard_label = ttk.Label(
            self, text="Heard: ", font=("Segoe UI", 9, "italic"), foreground="#555555"
        )
        self.heard_label.pack(anchor="w", padx=16, pady=(0, 8))

        # Two-column body
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_calendar_panel(body)
        self._build_notes_panel(body)

    def _build_calendar_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="Calendar")
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Month navigation
        nav = ttk.Frame(panel)
        nav.pack(fill="x", padx=10, pady=(10, 4))

        ttk.Button(nav, text="‹", width=3, command=self.prev_month).pack(side="left")
        self.month_label = ttk.Label(nav, text="", font=("Segoe UI", 11, "bold"), anchor="center")
        self.month_label.pack(side="left", expand=True)
        ttk.Button(nav, text="›", width=3, command=self.next_month).pack(side="right")
        ttk.Button(nav, text="Today", command=self.go_today).pack(side="right", padx=(0, 6))

        # Day grid — row 0 is the weekday headers, days get added below
        self.grid_frame = ttk.Frame(panel)
        self.grid_frame.pack(padx=10, pady=(4, 10))

        for col, name in enumerate(WEEKDAYS):
            ttk.Label(
                self.grid_frame, text=name, font=("Segoe UI", 9, "bold"), anchor="center", width=5
            ).grid(row=0, column=col, padx=1, pady=(0, 4))

        # Events for the selected day
        ttk.Label(panel, text="Events", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10)
        self.selected_label = ttk.Label(panel, text="", font=("Segoe UI", 9), foreground="#555555")
        self.selected_label.pack(anchor="w", padx=10, pady=(0, 4))

        events_frame = ttk.Frame(panel)
        events_frame.pack(fill="both", expand=True, padx=10)

        self.events_list = tk.Listbox(events_frame, font=("Segoe UI", 10), height=6)
        events_scroll = ttk.Scrollbar(events_frame, command=self.events_list.yview)
        self.events_list.configure(yscrollcommand=events_scroll.set)
        self.events_list.pack(side="left", fill="both", expand=True)
        events_scroll.pack(side="right", fill="y")

        event_entry_frame = ttk.Frame(panel)
        event_entry_frame.pack(fill="x", padx=10, pady=(6, 10))

        self.event_entry = ttk.Entry(event_entry_frame)
        self.event_entry.pack(side="left", fill="x", expand=True)
        self.event_entry.bind("<Return>", lambda e: self.add_event_from_entry())

        ttk.Button(event_entry_frame, text="Add", command=self.add_event_from_entry).pack(side="left", padx=(6, 0))
        ttk.Button(event_entry_frame, text="Delete", command=self.delete_selected_event).pack(side="left", padx=(6, 0))

    def _build_notes_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="Notepad")
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        notes_frame = ttk.Frame(panel)
        notes_frame.pack(fill="both", expand=True, padx=10, pady=(10, 4))

        self.notes_list = tk.Listbox(notes_frame, font=("Segoe UI", 10))
        notes_scroll = ttk.Scrollbar(notes_frame, command=self.notes_list.yview)
        self.notes_list.configure(yscrollcommand=notes_scroll.set)
        self.notes_list.pack(side="left", fill="both", expand=True)
        notes_scroll.pack(side="right", fill="y")

        ttk.Label(panel, text="New note:", font=("Segoe UI", 9)).pack(anchor="w", padx=10)

        self.note_text = tk.Text(panel, height=4, wrap="word", font=("Segoe UI", 10))
        self.note_text.pack(fill="x", padx=10, pady=(2, 6))

        note_btns = ttk.Frame(panel)
        note_btns.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(note_btns, text="Save note", command=self.add_note_from_entry).pack(side="left")
        ttk.Button(note_btns, text="Delete selected", command=self.delete_selected_note).pack(side="left", padx=(6, 0))

    # calendar
    def _refresh_calendar(self):
        # Rebuilds the day buttons for the currently viewed month.
        # Clear old day buttons (row 0 holds the weekday headers, keep those)
        for child in self.grid_frame.winfo_children():
            info = child.grid_info()
            if info and int(info["row"]) > 0:
                child.destroy()

        self.month_label.config(text=f"{calendar.month_name[self.view_month]} {self.view_year}")

        marked = self._days_with_events(self.view_year, self.view_month)
        today = date.today()

        # monthcalendar gives weeks as lists of day numbers, 0 = padding
        weeks = calendar.monthcalendar(self.view_year, self.view_month)
        for row, week in enumerate(weeks, start=1):
            for col, day in enumerate(week):
                if day == 0:
                    continue

                this_date = date(self.view_year, self.view_month, day)
                label = f"{day}•" if day in marked else str(day)

                btn = tk.Button(
                    self.grid_frame,
                    text=label,
                    width=5,
                    font=("Segoe UI", 9),
                    relief="flat",
                    command=lambda d=this_date: self.select_date(d),
                )

                if this_date == self.selected_date:
                    btn.config(bg="#2eb82e", fg="white")
                elif this_date == today:
                    btn.config(bg="#e6e6e6")

                btn.grid(row=row, column=col, padx=1, pady=1)

    def _days_with_events(self, year, month):
        #Day numbers in this month that have at least one event, so the grid can mark them
        prefix = f"{year:04d}-{month:02d}-"
        days = set()
        for date_str in self.events:
            if date_str.startswith(prefix):
                days.add(int(date_str.split("-")[2]))
        return days

    def select_date(self, new_date):
        self.selected_date = new_date
        self._refresh_calendar()
        self._refresh_events()

    def prev_month(self):
        # Step back a day from the 1st to land in the previous month
        # avoids hand-rolling the year rollover.
        first = date(self.view_year, self.view_month, 1)
        previous = first - timedelta(days=1)
        self.view_year, self.view_month = previous.year, previous.month
        self._refresh_calendar()

    def next_month(self):
        last_day = calendar.monthrange(self.view_year, self.view_month)[1]
        following = date(self.view_year, self.view_month, last_day) + timedelta(days=1)
        self.view_year, self.view_month = following.year, following.month
        self._refresh_calendar()

    def go_today(self):
        today = date.today()
        self.view_year, self.view_month = today.year, today.month
        self.select_date(today)

    # events 
    def _date_key(self):
        return self.selected_date.strftime("%Y-%m-%d")

    def _refresh_events(self):
        self.selected_label.config(text=self.selected_date.strftime("%A, %d %B %Y"))
        self.events_list.delete(0, "end")
        self._event_ids = []
        for event in self.events.get(self._date_key(), []):
            self.events_list.insert("end", event["text"])
            self._event_ids.append(event["id"])

    def add_event(self, text):
        text = text.strip()
        if not text:
            return
        events_for_day = self.events.setdefault(self._date_key(), [])
        events_for_day.append({"id": self._next_event_id, "text": text})
        self._next_event_id += 1
        self._refresh_events()
        self._refresh_calendar()  # so the day picks up its marker

    def add_event_from_entry(self):
        self.add_event(self.event_entry.get())
        self.event_entry.delete(0, "end")

    def delete_selected_event(self):
        selection = self.events_list.curselection()
        if not selection:
            return
        event_id = self._event_ids[selection[0]]
        key = self._date_key()
        self.events[key] = [e for e in self.events.get(key, []) if e["id"] != event_id]
        if not self.events[key]:
            del self.events[key]
        self._refresh_events()
        self._refresh_calendar()

    # notes
    def _refresh_notes(self):
        self.notes_list.delete(0, "end")
        self._note_ids = []
        # Newest first — most recent thought is the one you want to see.
        for note in sorted(self.notes, key=lambda n: n["id"], reverse=True):
            self.notes_list.insert("end", f"[{note['created']}]  {note['text']}")
            self._note_ids.append(note["id"])

    def add_note(self, text):
        text = text.strip()
        if not text:
            return
        self.notes.append({
            "id": self._next_note_id,
            "text": text,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        self._next_note_id += 1
        self._refresh_notes()

    def add_note_from_entry(self):
        self.add_note(self.note_text.get("1.0", "end"))
        self.note_text.delete("1.0", "end")

    def delete_selected_note(self):
        selection = self.notes_list.curselection()
        if not selection:
            return
        note_id = self._note_ids[selection[0]]
        self.notes = [n for n in self.notes if n["id"] != note_id]
        self._refresh_notes()

    # voice
    def handle_voice(self, text):
        # Called by the hub with each finalized phrase while this window is open
        self.heard_label.config(text=f"Heard: {text}")
        lowered = text.lower().strip()

        # Navigation first — checked before the note/event prefixes so
        # "go back" can't accidentally get eaten as note text.
        if lowered in ("go back", "main menu", "close", "back to hub"):
            self.close()
            return
        if lowered == "next month":
            self.next_month()
            return
        if lowered in ("last month", "previous month"):
            self.prev_month()
            return
        if lowered in ("today", "go to today"):
            self.go_today()
            return

        # Content commands — everything after the keyword is the
        # payload, sliced from the ORIGINAL text (not lowered) so notes
        # and events keep their natural capitalization.
        for prefix in ("add note ", "new note ", "note "):
            if lowered.startswith(prefix):
                self.add_note(text[len(prefix):])
                self._say("Note saved")
                return

        for prefix in ("add event ", "new event ", "event "):
            if lowered.startswith(prefix):
                self.add_event(text[len(prefix):])
                self._say("Event added")
                return

        # Didn't match anything — heard_label already shows what came
        # through, so just leave it at that rather than guessing.

    def _say(self, message):
        if self.speaker:
            self.speaker.say(message)

    def close(self):
        if self._on_close_callback:
            self._on_close_callback()
        self.destroy()

# Lets you run this file on its own to check the layout. The hidden root
# window is just scaffolding — main.py will pass in the real hub window
# as the parent later.
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    window = SecondBrainWindow(root)
    window.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()