import tkinter as tk
from datetime import datetime, timedelta

SNOOZE_MINUTES = 5
RING_SECONDS = 60
TICK_MS = 500

BG = "#14161c"
PANEL = "#1e222b"
FG = "#e8e8e8"
MUTED = "#8a93a6"
ACCENT = "#4da3ff"
RED = "#e74c3c"


def two(n):
    return str(n).zfill(2)


def sort_key(alarm):
    return alarm.hour * 60 + alarm.minute


class Alarm:
    def __init__(self, hour, minute, label, once):
        self.hour = hour
        self.minute = minute
        self.label = label
        self.once = once
        self.on = True
        self.fired = False

    def time_text(self):
        return two(self.hour) + ":" + two(self.minute)

    def describe(self):
        text = self.time_text()
        if self.label != "":
            text += "   " + self.label
        if self.once:
            text += "   (once)"
        if not self.on:
            text += "   (off)"
        return text

    def matches(self, now):
        return self.on and now.hour == self.hour and now.minute == self.minute

    def minutes_until(self, now):
        diff = self.hour * 60 + self.minute - (now.hour * 60 + now.minute)
        if diff <= 0:
            diff += 24 * 60
        return diff


class App:
    def __init__(self, root):
        self.root = root
        root.title("Alarm Clock")
        root.configure(bg=BG)
        root.resizable(False, False)

        self.alarms = []
        self.ringing = None
        self.ring_ticks = 0

        self.build_clock()
        self.build_form()
        self.build_list()
        self.build_ring()

        self.fill_default_time()
        self.tick()

    def build_clock(self):
        self.clock_label = tk.Label(self.root, text="", bg=BG, fg=FG,
                                    font="Courier 54 bold")
        self.clock_label.pack(padx=30, pady=(20, 0))

        self.date_label = tk.Label(self.root, text="", bg=BG, fg=MUTED,
                                   font="Helvetica 13")
        self.date_label.pack()

        self.next_label = tk.Label(self.root, text="", bg=BG, fg=ACCENT,
                                   font="Helvetica 12")
        self.next_label.pack(pady=(4, 12))

    def build_form(self):
        box = tk.Frame(self.root, bg=PANEL)
        box.pack(fill="x", padx=20, pady=6)

        row = tk.Frame(box, bg=PANEL)
        row.pack(padx=12, pady=(12, 6))

        self.hour_box = tk.Spinbox(row, from_=0, to=23, width=3, wrap=True,
                                   font="Courier 20", format="%02.0f")
        self.hour_box.pack(side="left")

        tk.Label(row, text=":", bg=PANEL, fg=FG, font="Courier 20 bold").pack(side="left")

        self.minute_box = tk.Spinbox(row, from_=0, to=59, width=3, wrap=True,
                                     font="Courier 20", format="%02.0f")
        self.minute_box.pack(side="left")

        self.label_entry = tk.Entry(row, width=16, font="Helvetica 13")
        self.label_entry.pack(side="left", padx=(14, 0))

        row2 = tk.Frame(box, bg=PANEL)
        row2.pack(padx=12, pady=(0, 12), fill="x")

        self.once_var = tk.IntVar(value=0)
        tk.Checkbutton(row2, text="ring once", variable=self.once_var,
                       bg=PANEL, fg=FG, selectcolor=BG, activebackground=PANEL,
                       activeforeground=FG).pack(side="left")

        tk.Button(row2, text="Add alarm", command=self.add_alarm,
                  bg=ACCENT, fg="black", relief="flat", padx=14).pack(side="right")

        self.status = tk.Label(self.root, text="", bg=BG, fg=RED, font="Helvetica 11")
        self.status.pack()

    def build_list(self):
        self.listbox = tk.Listbox(self.root, height=6, width=44, bg=PANEL, fg=FG,
                                  selectbackground=ACCENT, selectforeground="black",
                                  font="Courier 13", relief="flat",
                                  highlightthickness=0, activestyle="none")
        self.listbox.pack(padx=20, pady=(4, 6))

        row = tk.Frame(self.root, bg=BG)
        row.pack(pady=(0, 10))
        tk.Button(row, text="On / Off", command=self.toggle_alarm,
                  relief="flat", padx=12).pack(side="left", padx=4)
        tk.Button(row, text="Delete", command=self.delete_alarm,
                  relief="flat", padx=12).pack(side="left", padx=4)

    def build_ring(self):
        self.ring_label = tk.Label(self.root, text="no alarm ringing", bg=PANEL,
                                   fg=MUTED, font="Helvetica 16 bold", pady=14)
        self.ring_label.pack(fill="x", padx=20)

        row = tk.Frame(self.root, bg=BG)
        row.pack(pady=12)

        self.snooze_button = tk.Button(row, text="Snooze " + str(SNOOZE_MINUTES) + " min",
                                       command=self.snooze, state="disabled",
                                       relief="flat", padx=16, pady=4)
        self.snooze_button.pack(side="left", padx=6)

        self.stop_button = tk.Button(row, text="Stop", command=self.stop_ring,
                                     state="disabled", relief="flat", padx=16, pady=4)
        self.stop_button.pack(side="left", padx=6)

    def fill_default_time(self):
        later = datetime.now() + timedelta(minutes=1)
        self.hour_box.delete(0, "end")
        self.hour_box.insert(0, two(later.hour))
        self.minute_box.delete(0, "end")
        self.minute_box.insert(0, two(later.minute))

    def refresh_list(self):
        self.alarms.sort(key=sort_key)
        self.listbox.delete(0, "end")
        for alarm in self.alarms:
            self.listbox.insert("end", alarm.describe())

    def selected_index(self):
        picked = self.listbox.curselection()
        if len(picked) == 0:
            return -1
        return picked[0]

    def add_alarm(self):
        hour_text = self.hour_box.get().strip()
        minute_text = self.minute_box.get().strip()

        if not hour_text.isdigit() or not minute_text.isdigit():
            self.status.config(text="hour and minute must be numbers")
            return

        hour = int(hour_text)
        minute = int(minute_text)
        if hour > 23 or minute > 59:
            self.status.config(text="hour is 0-23, minute is 0-59")
            return

        label = self.label_entry.get().strip()
        alarm = Alarm(hour, minute, label, self.once_var.get() == 1)
        self.alarms.append(alarm)
        self.refresh_list()
        self.label_entry.delete(0, "end")
        self.status.config(text="")

    def toggle_alarm(self):
        i = self.selected_index()
        if i == -1:
            self.status.config(text="select an alarm first")
            return
        self.alarms[i].on = not self.alarms[i].on
        self.status.config(text="")
        self.refresh_list()
        self.listbox.selection_set(i)

    def delete_alarm(self):
        i = self.selected_index()
        if i == -1:
            self.status.config(text="select an alarm first")
            return
        if self.alarms[i] is self.ringing:
            self.stop_ring()
        self.alarms.pop(i)
        self.status.config(text="")
        self.refresh_list()

    def check_alarms(self, now):
        for alarm in self.alarms:
            if alarm.matches(now):
                if not alarm.fired and self.ringing is None:
                    alarm.fired = True
                    self.start_ring(alarm)
            else:
                alarm.fired = False

    def start_ring(self, alarm):
        self.ringing = alarm
        self.ring_ticks = 0
        name = alarm.time_text()
        if alarm.label != "":
            name = alarm.label + "  " + name
        self.ring_label.config(text="ALARM  " + name)
        self.snooze_button.config(state="normal")
        self.stop_button.config(state="normal")

    def ring_step(self):
        self.ring_ticks += 1
        if self.ring_ticks % 2 == 0:
            self.ring_label.config(bg=RED, fg="white")
            self.root.bell()
        else:
            self.ring_label.config(bg=PANEL, fg=RED)
        if self.ring_ticks >= RING_SECONDS * 1000 // TICK_MS:
            self.stop_ring()

    def stop_ring(self):
        alarm = self.ringing
        if alarm is None:
            return
        self.ringing = None
        self.ring_label.config(text="no alarm ringing", bg=PANEL, fg=MUTED)
        self.snooze_button.config(state="disabled")
        self.stop_button.config(state="disabled")
        if alarm.once and alarm in self.alarms:
            self.alarms.remove(alarm)
            self.refresh_list()

    def snooze(self):
        if self.ringing is None:
            return
        later = datetime.now() + timedelta(minutes=SNOOZE_MINUTES)
        extra = Alarm(later.hour, later.minute, "snooze", True)
        self.alarms.append(extra)
        self.stop_ring()
        self.refresh_list()

    def next_text(self, now):
        best = -1
        for alarm in self.alarms:
            if not alarm.on:
                continue
            mins = alarm.minutes_until(now)
            if best == -1 or mins < best:
                best = mins
        if best == -1:
            return "no alarms set"
        hours = best // 60
        mins = best % 60
        return "next alarm in " + str(hours) + "h " + two(mins) + "m"

    def tick(self):
        now = datetime.now()
        self.clock_label.config(text=now.strftime("%H:%M:%S"))
        self.date_label.config(text=now.strftime("%A, %d %B %Y"))
        self.check_alarms(now)
        if self.ringing is not None:
            self.ring_step()
        self.next_label.config(text=self.next_text(now))
        self.root.after(TICK_MS, self.tick)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()