import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont
import datetime
import json
import os
import sys
import winreg
import threading
import subprocess
import tempfile

try:
    import pystray
    from PIL import Image, ImageDraw
    _has_tray = True
except ImportError:
    _has_tray = False

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timergoal_data.json")
APP_NAME  = "TimerGoal"
APP_PATH  = f'pythonw "{os.path.abspath(__file__)}"'

BG       = "#111111"
BAR      = "#1C1C1C"
CARD     = "#1A1A1A"
ACCENT   = "#7C6EFA"
SUCCESS  = "#4ADE80"
RED      = "#EF4444"
TEXT_PRI = "#F0F0F0"
TEXT_SEC = "#888888"
TEXT_DIM = "#444444"
BORDER   = "#2A2A2A"

_has_inter = False


def F(size, weight="normal"):
    return ("Inter" if _has_inter else "Segoe UI", size, weight)


# ── tray icon image ───────────────────────────────────────────────────────────

def _make_icon_image(size=64):
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded-square background
    r = max(4, size // 5)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill="#7C6EFA")

    # Hourglass — matches CSS clip-path polygon(8% 0%, 92% 0%, 58% 50%, 92% 100%, 8% 100%, 42% 50%)
    s = size
    hg = [
        (s * 0.08, s * 0.18),   # top-left
        (s * 0.92, s * 0.18),   # top-right
        (s * 0.58, s * 0.50),   # neck-right
        (s * 0.92, s * 0.82),   # bottom-right
        (s * 0.08, s * 0.82),   # bottom-left
        (s * 0.42, s * 0.50),   # neck-left
    ]
    draw.polygon(hg, fill="white")

    return img.convert("RGB")


def _ensure_ico() -> str:
    ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timergoal.ico")
    if not os.path.exists(ico_path):
        try:
            img = _make_icon_image(256)
            img.save(ico_path, format="ICO",
                     sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        except Exception:
            return ""
    return ico_path


# ── desktop shortcut ──────────────────────────────────────────────────────────

def _get_desktop() -> str:
    try:
        r = subprocess.run(
            ["powershell", "-Command", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return os.path.join(os.path.expanduser("~"), "Desktop")


def create_desktop_shortcut() -> bool:
    script_path = os.path.abspath(__file__)
    script_dir  = os.path.dirname(script_path)
    desktop     = _get_desktop()
    shortcut    = os.path.join(desktop, f"{APP_NAME}.lnk")
    icon        = _ensure_ico() if _has_tray else ""
    icon_loc    = f"{icon},0" if icon else ""

    lines = [
        "$ws = New-Object -ComObject WScript.Shell",
        f"$s  = $ws.CreateShortcut('{shortcut}')",
        "$s.TargetPath       = 'pythonw'",
        f"$s.Arguments       = '\"{script_path}\"'",
        f"$s.WorkingDirectory = '{script_dir}'",
        "$s.Description     = 'TimerGoal'",
    ]
    if icon_loc:
        lines.append(f"$s.IconLocation = '{icon_loc}'")
    lines.append("$s.Save()")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ps1", delete=False, encoding="utf-8"
    ) as f:
        f.write("\n".join(lines))
        tmp = f.name

    try:
        r = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", tmp],
            capture_output=True, timeout=10,
        )
        return r.returncode == 0
    except Exception:
        return False
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


# ── startup helpers ───────────────────────────────────────────────────────────

def _reg_key():
    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_ALL_ACCESS,
    )

def is_startup_enabled() -> bool:
    try:
        with _reg_key() as k:
            winreg.QueryValueEx(k, APP_NAME)
            return True
    except FileNotFoundError:
        return False

def set_startup(enable: bool):
    try:
        with _reg_key() as k:
            if enable:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, APP_PATH)
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
    except Exception as e:
        messagebox.showerror("Startup Error", str(e))


# ── settings dialog ───────────────────────────────────────────────────────────

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, data: dict, on_save):
        super().__init__(parent)
        self.on_save = on_save
        self.data    = data

        self.title("Settings")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        W, H = 300, 360
        px = parent.winfo_x() - W - 8
        py = parent.winfo_y()
        if px < 0:
            px = parent.winfo_x() + parent.winfo_width() + 8
        self.geometry(f"{W}x{H}+{px}+{py}")

        self.grab_set()
        self._build()

    def _build(self):
        pad = 20

        tk.Label(self, text="Settings", font=F(13, "bold"),
                 fg=TEXT_PRI, bg=BG).pack(anchor="w", padx=pad, pady=(18, 14))

        # Goal
        tk.Label(self, text="Goal / Objective", font=F(9),
                 fg=TEXT_SEC, bg=BG).pack(anchor="w", padx=pad)

        self._goal_var = tk.StringVar(value=self.data.get("goal", ""))
        goal_entry = tk.Entry(self, textvariable=self._goal_var,
                              font=F(11), fg=TEXT_PRI, bg=CARD,
                              bd=0, relief="flat", insertbackground=TEXT_PRI,
                              highlightthickness=1,
                              highlightcolor=ACCENT,
                              highlightbackground=BORDER)
        goal_entry.pack(fill="x", padx=pad, pady=(4, 14), ipady=7)
        goal_entry.focus_set()

        # Target date
        tk.Label(self, text="Target Date  (YYYY-MM-DD)", font=F(9),
                 fg=TEXT_SEC, bg=BG).pack(anchor="w", padx=pad)

        self._date_var = tk.StringVar(value=self.data.get("target_date", ""))
        date_entry = tk.Entry(self, textvariable=self._date_var,
                              font=F(11), fg=TEXT_PRI, bg=CARD,
                              bd=0, relief="flat", insertbackground=TEXT_PRI,
                              highlightthickness=1,
                              highlightcolor=ACCENT,
                              highlightbackground=BORDER)
        date_entry.pack(fill="x", padx=pad, pady=(4, 14), ipady=7)
        date_entry.bind("<Return>", self._save)

        # Startup toggle
        self._startup_var = tk.BooleanVar(value=is_startup_enabled())
        startup_row = tk.Frame(self, bg=BG)
        startup_row.pack(fill="x", padx=pad, pady=(0, 10))

        tk.Checkbutton(
            startup_row, variable=self._startup_var,
            text="Run on Windows startup",
            font=F(10), fg=TEXT_SEC, bg=BG,
            activebackground=BG, activeforeground=TEXT_PRI,
            selectcolor=CARD, bd=0, cursor="hand2",
        ).pack(side="left")

        # Desktop shortcut
        tk.Button(
            self, text="Create Desktop Shortcut", font=F(10),
            fg=TEXT_SEC, bg=CARD, bd=0, relief="flat",
            cursor="hand2", padx=14, pady=5,
            command=self._make_shortcut,
        ).pack(fill="x", padx=pad, pady=(0, 14))

        # Save / Cancel
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=pad)

        tk.Button(btn_row, text="Cancel", font=F(10),
                  fg=TEXT_SEC, bg=CARD, bd=0, relief="flat",
                  cursor="hand2", padx=14, pady=6,
                  command=self.destroy).pack(side="left")

        tk.Button(btn_row, text="Save", font=F(10, "bold"),
                  fg="#111", bg=ACCENT, bd=0, relief="flat",
                  cursor="hand2", padx=20, pady=6,
                  command=self._save).pack(side="right")

    def _make_shortcut(self):
        if create_desktop_shortcut():
            messagebox.showinfo("Done", "Desktop shortcut created successfully!", parent=self)
        else:
            messagebox.showerror("Error", "Could not create desktop shortcut.", parent=self)

    def _save(self, _=None):
        goal = self._goal_var.get().strip()
        date_raw = self._date_var.get().strip()

        if not goal:
            messagebox.showwarning("Missing", "Please enter a goal.", parent=self)
            return

        parsed_date = ""
        if date_raw:
            ok = False
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    parsed_date = datetime.datetime.strptime(date_raw, fmt).strftime("%Y-%m-%d")
                    ok = True
                    break
                except ValueError:
                    continue
            if not ok:
                messagebox.showwarning(
                    "Invalid Date",
                    "Use YYYY-MM-DD format (e.g. 2026-12-31).",
                    parent=self,
                )
                return

        set_startup(self._startup_var.get())
        self.on_save({"goal": goal, "target_date": parsed_date})
        self.destroy()


# ── main widget ───────────────────────────────────────────────────────────────

class TimerGoalApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        W, H = 280, 160
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{sw - W - 20}+{sh - H - 60}")

        self._drag_ox = self._drag_oy = 0
        self._data = self._load()
        self._settings_win = None
        self._tray = None

        self._build()
        self._refresh()

        if _has_tray:
            _ensure_ico()
            self._start_tray()

    # ── tray ──────────────────────────────────────────────────────────────────

    def _start_tray(self):
        ico  = _make_icon_image(64)
        menu = pystray.Menu(
            pystray.MenuItem("Show TimerGoal", self._show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._quit_app),
        )
        self._tray = pystray.Icon(APP_NAME, ico, APP_NAME, menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _hide_window(self):
        self.root.withdraw()

    def _show_window(self, _icon=None, _item=None):
        # called from pystray thread — schedule on main thread
        self.root.after(0, self._do_show)

    def _do_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)

    def _quit_app(self, icon=None, item=None):
        # called from pystray thread — schedule on main thread
        self.root.after(0, self._do_quit)

    def _do_quit(self):
        if self._tray:
            self._tray.stop()
        self.root.quit()

    # ── persistence ───────────────────────────────────────────────────────────

    def _load(self):
        default = {"goal": "Set your goal →", "target_date": ""}
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    default.update(d)
            except Exception:
                pass
        return default

    def _save(self, new_data: dict):
        self._data.update(new_data)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False)
        self._refresh()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        bar = tk.Frame(self.root, bg=BAR, height=26)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        title_lbl = tk.Label(bar, text=APP_NAME, font=F(8), fg=TEXT_DIM, bg=BAR)
        title_lbl.pack(side="left", padx=10)

        # Buttons — bind BEFORE attaching drag to avoid overwriting these bindings
        close_cmd = self._hide_window if _has_tray else self._do_quit
        close_btn = tk.Label(bar, text="×", font=F(12), fg=TEXT_SEC, bg=BAR,
                             cursor="hand2", padx=7)
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda _: close_cmd())

        gear_btn = tk.Label(bar, text="⚙", font=F(12), fg=TEXT_SEC, bg=BAR,
                            cursor="hand2", padx=7)
        gear_btn.pack(side="right")
        gear_btn.bind("<Button-1>", lambda _: self._open_settings())

        # Drag only on bar background and title label — NOT on buttons
        for w in (bar, title_lbl):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_move)

        # body
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(10, 14))

        self._goal_lbl = tk.Label(
            body, text="", font=F(11, "bold"), fg=TEXT_PRI, bg=BG,
            anchor="w", wraplength=248, justify="left", cursor="hand2",
        )
        self._goal_lbl.pack(fill="x")
        self._goal_lbl.bind("<Button-1>", lambda _: self._open_settings())

        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", pady=(6, 0))

        self._days_var = tk.StringVar(value="—")
        self._days_lbl = tk.Label(row, textvariable=self._days_var,
                                  font=F(44, "bold"), fg=ACCENT, bg=BG)
        self._days_lbl.pack(side="left")

        info = tk.Frame(row, bg=BG)
        info.pack(side="left", padx=(10, 0), anchor="s", pady=(0, 6))

        tk.Label(info, text="days left", font=F(10), fg=TEXT_SEC,
                 bg=BG, anchor="w").pack(anchor="w")

        self._until_lbl = tk.Label(info, text="", font=F(8),
                                   fg=TEXT_DIM, bg=BG, anchor="w", cursor="hand2")
        self._until_lbl.pack(anchor="w")
        self._until_lbl.bind("<Button-1>", lambda _: self._open_settings())

    # ── drag ─────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._drag_ox = e.x_root - self.root.winfo_x()
        self._drag_oy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._drag_ox}+{e.y_root - self._drag_oy}")

    # ── settings ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.lift()
            return
        self._settings_win = SettingsDialog(self.root, self._data, self._save)

    # ── refresh ───────────────────────────────────────────────────────────────

    def _refresh(self):
        goal = self._data.get("goal", "")
        self._goal_lbl.config(text=goal)

        target_str = self._data.get("target_date", "")
        if target_str:
            try:
                target = datetime.datetime.strptime(target_str, "%Y-%m-%d").date()
                today  = datetime.date.today()
                delta  = (target - today).days
                display = max(delta, 0)
                self._days_var.set(str(display))
                color = RED if delta <= 7 else ACCENT
                self._days_lbl.config(fg=color)
                self._until_lbl.config(
                    text=f"until {target.strftime('%d %b %Y')}",
                    fg=RED if delta <= 7 else TEXT_DIM,
                )
            except ValueError:
                self._days_var.set("—")
                self._until_lbl.config(text="invalid date", fg=RED)
        else:
            self._days_var.set("—")
            self._until_lbl.config(text="⚙ click to set date", fg=TEXT_DIM)

        self.root.after(60_000, self._refresh)


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    _has_inter = (
        tkfont.Font(family="Inter", size=12).actual("family").lower() == "inter"
    )
    root.deiconify()
    TimerGoalApp(root)
    root.mainloop()
