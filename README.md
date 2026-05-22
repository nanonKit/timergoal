# TimerGoal

A minimal always-on-top desktop widget for Windows that counts down the days remaining until your goal.

![TimerGoal widget screenshot](https://raw.githubusercontent.com/nanonKit/timergoal/master/preview.png)

---

## What it does

TimerGoal sits quietly in the corner of your screen and reminds you every single day how many days you have left to reach your goal. No noise, no notifications — just a persistent, honest countdown.

---

## Features

- **Live countdown** — days remaining update automatically every minute
- **Always on top** — stays visible over other windows
- **Draggable** — click and drag anywhere on the title bar to reposition
- **System tray** — closing the widget hides it to the tray; the app keeps running in the background
- **Desktop shortcut** — one-click shortcut creation from the Settings menu
- **Run on startup** — optional Windows registry entry to launch at login
- **Colour feedback** — counter turns red when fewer than 7 days remain

---

## Requirements

- Windows 10 / 11
- Python 3.8+
- [Pillow](https://pypi.org/project/Pillow/) and [pystray](https://pypi.org/project/pystray/) for the system tray and icon

Install dependencies:

```bash
pip install pillow pystray
```

---

## Getting started

```bash
git clone https://github.com/nanonKit/timergoal.git
cd timerGoal
pip install pillow pystray
pythonw timerGoal.py
```

> Use `pythonw` instead of `python` to run without a console window.

---

## How to use

| Action | What to do |
|---|---|
| Set / edit your goal | Click the goal text or the ⚙ icon |
| Move the widget | Click and drag the title bar |
| Hide to tray | Click **×** |
| Show again | Double-click the tray icon, or right-click → **Show TimerGoal** |
| Quit completely | Right-click the tray icon → **Exit** |
| Create a desktop shortcut | ⚙ Settings → **Create Desktop Shortcut** |
| Run on Windows startup | ⚙ Settings → check **Run on Windows startup** |

### Setting a goal

1. Click ⚙ or click anywhere on the goal text.
2. Enter your goal name and target date (`YYYY-MM-DD`).
3. Click **Save**.

The widget immediately shows the updated countdown.

---

## File structure

```
timerGoal/
├── timerGoal.py          # main application
├── timergoal_data.json   # saved goal and target date (auto-created)
├── timergoal.ico         # tray / shortcut icon (auto-created)
└── icon_design.html      # CSS mockup of the icon design
```

---

## Built with

- [tkinter](https://docs.python.org/3/library/tkinter.html) — UI
- [pystray](https://github.com/moses-palmer/pystray) — system tray
- [Pillow](https://python-pillow.org/) — icon generation

---

## License

MIT
