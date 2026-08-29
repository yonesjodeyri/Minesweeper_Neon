from __future__ import annotations

import json
import math
import random
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

APP = "Minesweeper: Neon Protocol"
ROOT = Path(__file__).resolve().parent
DATA_FILE = Path.home() / ".minesweeper_neon_protocol.json"
SOUND_DIR = ROOT / "sounds"

THEMES = {
    "Neon Dark": dict(bg="#080b16", panel="#10172b", panel2="#17223c", tile="#1d2a49",
                      hover="#294069", revealed="#0d1426", text="#edf5ff", muted="#91a4c8",
                      accent="#63e6ff", accent2="#9d7bff", danger="#ff5f7a", good="#54e39a",
                      gold="#ffd166"),
    "Cyber Purple": dict(bg="#0d0815", panel="#1a1028", panel2="#29153f", tile="#382052",
                         hover="#4b2d69", revealed="#160e21", text="#fff2ff", muted="#b79bc9",
                         accent="#db8cff", accent2="#758cff", danger="#ff668c", good="#65e5a1",
                         gold="#ffd166"),
    "Midnight Blue": dict(bg="#06101c", panel="#0c1b2c", panel2="#142a42", tile="#1c3a59",
                          hover="#285376", revealed="#091724", text="#edf8ff", muted="#91b1ca",
                          accent="#61c7ff", accent2="#6d91ff", danger="#ff6879", good="#5de3ad",
                          gold="#ffd166"),
}

MODES = {
    "Rookie": (9, 9, 10),
    "Tactician": (16, 16, 40),
    "Veteran": (24, 16, 60),
}


def default_profile():
    return {
        "xp": 0, "level": 1, "coins": 0, "sound": True,
        "theme": "Neon Dark", "scores": [], "achievements": [],
        "games": 0, "wins": 0
    }


def load_profile():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        base = default_profile()
        base.update(data)
        return base
    except Exception:
        return default_profile()


def save_profile(data):
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class Sound:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def play(self, name):
        if not self.enabled:
            return
        path = SOUND_DIR / f"{name}.wav"
        if not path.exists():
            return
        threading.Thread(target=self._play, args=(path,), daemon=True).start()

    def _play(self, path):
        try:
            if sys.platform.startswith("win"):
                import winsound
                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            for cmd in (["paplay", str(path)], ["aplay", str(path)]):
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except FileNotFoundError:
                    pass
        except Exception:
            pass


class Minesweeper:
    def __init__(self, root):
        self.root = root
        self.profile = load_profile()
        self.theme = THEMES.get(self.profile["theme"], THEMES["Neon Dark"])
        self.sound = Sound(self.profile["sound"])

        self.rows = 9
        self.cols = 9
        self.mines = 10
        self.state = "ready"
        self.first_click = True
        self.start_time = None
        self.elapsed = 0
        self.hover = None
        self.hint_cell = None
        self.history = []
        self.future = []
        self.cells = []

        self.root.title(APP)
        self.root.geometry("1100x780")
        self.root.minsize(900, 680)
        self.root.configure(bg=self.theme["bg"])

        self.root.bind("<F2>", lambda e: self.new_game())
        self.root.bind("<Control-r>", lambda e: self.new_game())
        self.root.bind("<space>", lambda e: self.toggle_pause())
        self.root.bind("<Escape>", lambda e: self.menu())
        self.root.bind("<h>", lambda e: self.hint())
        self.root.bind("<H>", lambda e: self.hint())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())

        self.show_menu()
        self.root.after(100, self.tick)

    # ---------- generic UI ----------

    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def button(self, parent, text, command, primary=False):
        return tk.Button(
            parent, text=text, command=command,
            font=("Segoe UI", 10, "bold"), bd=0, relief="flat",
            fg=self.theme["text"],
            bg=self.theme["accent"] if primary else self.theme["panel2"],
            activebackground=self.theme["accent2"],
            activeforeground=self.theme["text"],
            padx=16, pady=9, cursor="hand2"
        )

    def title(self, text, subtitle=""):
        tk.Label(self.root, text=text, font=("Segoe UI", 30, "bold"),
                 fg=self.theme["text"], bg=self.theme["bg"]).pack(pady=(32, 5))
        if subtitle:
            tk.Label(self.root, text=subtitle, font=("Segoe UI", 10),
                     fg=self.theme["muted"], bg=self.theme["bg"]).pack()

    # ---------- menu ----------

    def show_menu(self):
        self.clear()
        self.state = "menu"

        outer = tk.Frame(self.root, bg=self.theme["bg"])
        outer.pack(expand=True, fill="both")

        tk.Label(outer, text="MINESWEEPER", font=("Segoe UI", 44, "bold"),
                 fg=self.theme["text"], bg=self.theme["bg"]).pack(pady=(70, 0))
        tk.Label(outer, text="NEON PROTOCOL", font=("Segoe UI", 15, "bold"),
                 fg=self.theme["accent"], bg=self.theme["bg"]).pack()
        tk.Label(outer, text="A premium puzzle experience",
                 font=("Segoe UI", 10), fg=self.theme["muted"], bg=self.theme["bg"]).pack(pady=7)

        card = tk.Frame(outer, bg=self.theme["panel"], padx=42, pady=30)
        card.pack(pady=28)

        for text, command, primary in [
            ("PLAY", self.show_modes, True),
            ("LEADERBOARD", self.show_leaderboard, False),
            ("ACHIEVEMENTS", self.show_achievements, False),
            ("SETTINGS", self.show_settings, False),
            ("RESET PROGRESS", self.reset_progress, False),
            ("QUIT", self.root.destroy, False),
        ]:
            self.button(card, text, command, primary).pack(fill="x", pady=5)

        tk.Label(
            outer,
            text=f"LEVEL {self.profile['level']}   •   XP {self.profile['xp']}   •   ◈ {self.profile['coins']}",
            font=("Consolas", 11, "bold"), fg=self.theme["gold"], bg=self.theme["bg"]
        ).pack()

    def show_modes(self):
        self.clear()
        self.title("SELECT DIFFICULTY", "Choose your mission parameters")
        box = tk.Frame(self.root, bg=self.theme["panel"], padx=30, pady=25)
        box.pack(pady=25)

        for name, (r, c, m) in MODES.items():
            self.button(
                box, f"{name}    {c} × {r}    💣 {m}",
                lambda n=name: self.start_game(n),
                name == "Rookie"
            ).pack(fill="x", pady=6)

        self.button(box, "CUSTOM BOARD", self.custom_board).pack(fill="x", pady=6)
        self.button(box, "BACK", self.show_menu).pack(fill="x", pady=(18, 0))

    def custom_board(self):
        r = simpledialog.askinteger("Custom Board", "Rows (5–30):", initialvalue=12, minvalue=5, maxvalue=30)
        if r is None: return
        c = simpledialog.askinteger("Custom Board", "Columns (5–30):", initialvalue=12, minvalue=5, maxvalue=30)
        if c is None: return
        m = simpledialog.askinteger("Custom Board", f"Mines (1–{r*c-9}):",
                                     initialvalue=min(20, r*c-9), minvalue=1, maxvalue=r*c-9)
        if m is None: return
        self.rows, self.cols, self.mines = r, c, m
        self.new_game()

    # ---------- game ----------

    def new_game(self):
        self.first_click = True
        self.state = "ready"
        self.start_time = None
        self.elapsed = 0
        self.hover = None
        self.hint_cell = None
        self.history.clear()
        self.future.clear()
        self.cells = [
            [{"mine": False, "revealed": False, "flag": False, "number": 0}
             for _ in range(self.cols)]
            for _ in range(self.rows)
        ]
        self.show_game()

    def start_game(self, mode):
        if mode in MODES:
            self.rows, self.cols, self.mines = MODES[mode]
        self.new_game()

    def show_game(self):
        self.clear()
        self.state = "ready" if self.first_click else self.state

        top = tk.Frame(self.root, bg=self.theme["bg"])
        top.pack(fill="x", padx=22, pady=(18, 10))

        self.button(top, "☰ MENU", self.menu).pack(side="left")
        self.hud = tk.Label(top, text="", font=("Consolas", 13, "bold"),
                            fg=self.theme["text"], bg=self.theme["bg"])
        self.hud.pack(side="left", expand=True)

        self.button(top, "UNDO", self.undo).pack(side="right", padx=3)
        self.button(top, "REDO", self.redo).pack(side="right", padx=3)
        self.button(top, "HINT", self.hint).pack(side="right", padx=3)
        self.button(top, "NEW", self.new_game, True).pack(side="right", padx=3)

        panel = tk.Frame(self.root, bg=self.theme["panel"], padx=12, pady=12)
        panel.pack(expand=True, fill="both", padx=22, pady=(0, 10))

        self.canvas = tk.Canvas(
            panel, bg=self.theme["revealed"], highlightthickness=0,
            bd=0, cursor="crosshair"
        )
        self.canvas.pack(expand=True, fill="both")

        # Bind directly to the Canvas; no widgets sit over the board.
        self.canvas.bind("<Button-1>", self.on_left)
        self.canvas.bind("<Button-3>", self.on_right)
        self.canvas.bind("<Double-Button-1>", self.on_double)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", lambda e: self.set_hover(None))
        self.canvas.bind("<Configure>", lambda e: self.draw())

        tk.Label(
            self.root,
            text="LMB Reveal  •  RMB Flag  •  Double-click Chord  •  H Hint  •  Space Pause  •  Ctrl+Z/Y Undo/Redo",
            font=("Segoe UI", 8), fg=self.theme["muted"], bg=self.theme["bg"]
        ).pack(pady=(0, 12))

        self.canvas.focus_set()
        self.draw()

    def neighbors(self, r, c):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if not (dr or dc):
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < self.rows and 0 <= cc < self.cols:
                    yield rr, cc

    def generate(self, safe_r, safe_c):
        forbidden = {(safe_r, safe_c), *self.neighbors(safe_r, safe_c)}
        available = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in forbidden
        ]
        if len(available) < self.mines:
            available = [
                (r, c)
                for r in range(self.rows)
                for c in range(self.cols)
                if (r, c) != (safe_r, safe_c)
            ]
        for r, c in random.sample(available, self.mines):
            self.cells[r][c]["mine"] = True

        for r in range(self.rows):
            for c in range(self.cols):
                self.cells[r][c]["number"] = sum(
                    self.cells[a][b]["mine"] for a, b in self.neighbors(r, c)
                )

    def snapshot(self):
        return [[cell.copy() for cell in row] for row in self.cells]

    def restore(self, snap):
        self.cells = [[cell.copy() for cell in row] for row in snap]
        self.draw()

    def push_history(self):
        self.history.append(self.snapshot())
        if len(self.history) > 100:
            self.history.pop(0)
        self.future.clear()

    def reveal(self, r, c):
        if self.state in ("won", "lost", "paused"):
            return
        cell = self.cells[r][c]
        if cell["revealed"] or cell["flag"]:
            return

        if self.first_click:
            self.generate(r, c)
            self.first_click = False
            self.state = "running"
            self.start_time = time.monotonic()

        self.push_history()

        cell = self.cells[r][c]
        if cell["mine"]:
            self.sound.play("lose")
            cell["revealed"] = True
            self.state = "lost"
            for row in self.cells:
                for x in row:
                    if x["mine"]:
                        x["revealed"] = True
            self.draw()
            return

        self.flood(r, c)

        if self.check_win():
            self.state = "won"
            self.elapsed = int(time.monotonic() - self.start_time)
            self.sound.play("win")
            self.profile["games"] += 1
            self.profile["wins"] += 1
            self.add_xp(max(50, self.mines * 5))
            self.save_score()
            self.check_achievements()

        self.draw()

    def flood(self, r, c):
        stack = [(r, c)]
        seen = set()
        while stack:
            rr, cc = stack.pop()
            if (rr, cc) in seen:
                continue
            seen.add((rr, cc))
            cell = self.cells[rr][cc]
            if cell["mine"] or cell["flag"]:
                continue
            cell["revealed"] = True
            if cell["number"] == 0:
                stack.extend(self.neighbors(rr, cc))

    def toggle_flag(self, r, c):
        if self.state in ("won", "lost", "paused"):
            return
        cell = self.cells[r][c]
        if cell["revealed"]:
            return
        self.push_history()
        cell["flag"] = not cell["flag"]
        self.sound.play("flag" if cell["flag"] else "unflag")
        self.draw()

    def chord(self, r, c):
        cell = self.cells[r][c]
        if not cell["revealed"] or cell["number"] == 0:
            return
        flagged = sum(self.cells[a][b]["flag"] for a, b in self.neighbors(r, c))
        if flagged != cell["number"]:
            return
        for a, b in list(self.neighbors(r, c)):
            if not self.cells[a][b]["revealed"] and not self.cells[a][b]["flag"]:
                self.reveal(a, b)
                if self.state == "lost":
                    return

    def check_win(self):
        return all(cell["revealed"] or cell["mine"] for row in self.cells for cell in row)

    # ---------- events ----------

    def cell_at(self, x, y):
        if not hasattr(self, "canvas"):
            return None
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 10 or h < 10:
            return None
        size = max(20, min(48, int(min((w - 20) / self.cols, (h - 20) / self.rows))))
        ox = (w - size * self.cols) / 2
        oy = (h - size * self.rows) / 2
        c = int((x - ox) // size)
        r = int((y - oy) // size)
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return r, c
        return None

    def on_left(self, event):
        p = self.cell_at(event.x, event.y)
        if p:
            self.sound.play("click")
            self.reveal(*p)
        return "break"

    def on_right(self, event):
        p = self.cell_at(event.x, event.y)
        if p:
            self.toggle_flag(*p)
        return "break"

    def on_double(self, event):
        p = self.cell_at(event.x, event.y)
        if p:
            self.chord(*p)
        return "break"

    def on_motion(self, event):
        self.set_hover(self.cell_at(event.x, event.y))

    def set_hover(self, p):
        self.hover = p
        if hasattr(self, "canvas"):
            self.draw()

    # ---------- controls ----------

    def toggle_pause(self):
        if self.state == "running":
            self.elapsed = int(time.monotonic() - self.start_time)
            self.state = "paused"
        elif self.state == "paused":
            self.start_time = time.monotonic() - self.elapsed
            self.state = "running"
        else:
            return
        self.draw()

    def hint(self):
        if self.state != "running":
            return
        safe = [
            (r, c) for r in range(self.rows) for c in range(self.cols)
            if not self.cells[r][c]["revealed"]
            and not self.cells[r][c]["flag"]
            and not self.cells[r][c]["mine"]
        ]
        if not safe:
            return
        self.hint_cell = random.choice(safe)
        self.sound.play("hint")
        self.draw()
        self.root.after(900, self.clear_hint)

    def clear_hint(self):
        self.hint_cell = None
        self.draw()

    def undo(self):
        if not self.history or self.state in ("won", "lost"):
            return
        self.future.append(self.snapshot())
        self.restore(self.history.pop())

    def redo(self):
        if not self.future or self.state in ("won", "lost"):
            return
        self.history.append(self.snapshot())
        self.restore(self.future.pop())

    # ---------- progress ----------

    def add_xp(self, amount):
        self.profile["xp"] += amount
        while self.profile["xp"] >= self.profile["level"] * 500:
            self.profile["xp"] -= self.profile["level"] * 500
            self.profile["level"] += 1
            self.profile["coins"] += 50
            self.sound.play("levelup")
        save_profile(self.profile)

    def save_score(self):
        self.profile["scores"].append({
            "time": self.elapsed, "rows": self.rows,
            "cols": self.cols, "mines": self.mines,
            "date": time.strftime("%Y-%m-%d")
        })
        self.profile["scores"] = sorted(self.profile["scores"], key=lambda x: x["time"])[:50]
        save_profile(self.profile)

    def check_achievements(self):
        a = self.profile["achievements"]
        if "FIRST_CLEAR" not in a:
            a.append("FIRST_CLEAR")
        if self.elapsed <= 30 and "SPEEDRUN" not in a:
            a.append("SPEEDRUN")
        if self.mines >= 50 and "VETERAN" not in a:
            a.append("VETERAN")
        save_profile(self.profile)

    # ---------- screens ----------

    def show_leaderboard(self):
        self.clear()
        self.title("LEADERBOARD", "Local best runs")
        box = tk.Frame(self.root, bg=self.theme["panel"], padx=30, pady=20)
        box.pack(fill="x", padx=120)
        scores = self.profile["scores"]
        if not scores:
            tk.Label(box, text="No completed runs yet.",
                     fg=self.theme["muted"], bg=self.theme["panel"],
                     font=("Segoe UI", 12)).pack()
        for i, s in enumerate(scores, 1):
            tk.Label(
                box, text=f"{i:02d}   {s['time']:03d}s   {s['cols']}×{s['rows']}   💣 {s['mines']}   {s['date']}",
                fg=self.theme["text"], bg=self.theme["panel"],
                font=("Consolas", 10), anchor="w"
            ).pack(fill="x", pady=3)
        self.button(self.root, "BACK", self.show_menu).pack(pady=25)

    def show_achievements(self):
        self.clear()
        self.title("ACHIEVEMENTS", "Milestones and challenges")
        box = tk.Frame(self.root, bg=self.theme["panel"], padx=35, pady=25)
        box.pack(fill="x", padx=120)
        items = [
            ("FIRST_CLEAR", "First Contact", "Clear your first board."),
            ("SPEEDRUN", "Speed Demon", "Clear a board in 30 seconds."),
            ("VETERAN", "Veteran Protocol", "Clear a board containing 50+ mines."),
        ]
        for key, name, desc in items:
            unlocked = key in self.profile["achievements"]
            tk.Label(box, text=("✓ " if unlocked else "○ ") + name,
                     fg=self.theme["gold"] if unlocked else self.theme["muted"],
                     bg=self.theme["panel"], font=("Segoe UI", 13, "bold"),
                     anchor="w").pack(fill="x")
            tk.Label(box, text=desc, fg=self.theme["muted"], bg=self.theme["panel"],
                     font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=(0, 12))
        self.button(self.root, "BACK", self.show_menu).pack(pady=25)

    def show_settings(self):
        self.clear()
        self.title("SETTINGS", "Game configuration")
        box = tk.Frame(self.root, bg=self.theme["panel"], padx=35, pady=30)
        box.pack()

        tk.Label(box, text="THEME", fg=self.theme["text"], bg=self.theme["panel"],
                 font=("Segoe UI", 10, "bold")).pack(pady=(0, 8))
        theme_var = tk.StringVar(value=self.profile["theme"])

        def set_theme():
            self.profile["theme"] = theme_var.get()
            save_profile(self.profile)
            self.theme = THEMES[theme_var.get()]
            self.sound.play("ui")
            self.show_settings()

        for name in THEMES:
            tk.Radiobutton(
                box, text=name, variable=theme_var, value=name,
                command=set_theme, indicatoron=False,
                fg=self.theme["text"], bg=self.theme["panel2"],
                activebackground=self.theme["panel2"],
                selectcolor=self.theme["accent"], padx=15, pady=7
            ).pack(fill="x", pady=3)

        sound_var = tk.BooleanVar(value=self.profile["sound"])

        def toggle_sound():
            self.profile["sound"] = bool(sound_var.get())
            self.sound.enabled = self.profile["sound"]
            save_profile(self.profile)
            if self.sound.enabled:
                self.sound.play("ui")

        tk.Checkbutton(
            box, text="ENABLE SOUND EFFECTS",
            variable=sound_var, command=toggle_sound,
            fg=self.theme["text"], bg=self.theme["panel"],
            activebackground=self.theme["panel"],
            selectcolor=self.theme["panel2"],
            font=("Segoe UI", 10, "bold")
        ).pack(pady=(22, 5))

        tk.Label(box, text="Sound is enabled by default. Toggle it here.",
                 fg=self.theme["muted"], bg=self.theme["panel"],
                 font=("Segoe UI", 9)).pack()

        self.button(self.root, "RESET ALL PROGRESS", self.reset_progress).pack(pady=(22, 5))
        self.button(self.root, "BACK", self.show_menu).pack(pady=5)

    def reset_progress(self):
        if not messagebox.askyesno(
            "Reset Progress",
            "Reset XP, level, coins, leaderboard and achievements?\nThis cannot be undone."
        ):
            return
        self.profile = default_profile()
        self.sound.enabled = True
        save_profile(self.profile)
        self.theme = THEMES["Neon Dark"]
        self.sound.play("ui")
        self.show_menu()

    def menu(self):
        self.show_menu()

    def draw(self):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 10 or h < 10:
            return

        size = max(20, min(48, int(min((w - 20) / self.cols, (h - 20) / self.rows))))
        ox = (w - size * self.cols) / 2
        oy = (h - size * self.rows) / 2

        number_colors = ["", "#69a7ff", "#55d68a", "#ff697e", "#9b8cff",
                         "#ff9f43", "#46d9d0", "#f2f4f8", "#9aa6bf"]

        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.cells[r][c]
                x1 = ox + c * size + 1
                y1 = oy + r * size + 1
                x2 = x1 + size - 2
                y2 = y1 + size - 2

                if cell["revealed"]:
                    fill = "#4a1d2b" if cell["mine"] else self.theme["revealed"]
                else:
                    fill = self.theme["hover"] if self.hover == (r, c) else self.theme["tile"]

                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=fill,
                    outline=self.theme["panel2"]
                )

                if cell["flag"] and not cell["revealed"]:
                    self.canvas.create_text(
                        (x1+x2)/2, (y1+y2)/2, text="⚑",
                        fill=self.theme["danger"],
                        font=("Segoe UI Symbol", max(10, int(size*.42)), "bold")
                    )
                elif cell["revealed"] and cell["mine"]:
                    self.canvas.create_text(
                        (x1+x2)/2, (y1+y2)/2, text="✹",
                        fill=self.theme["danger"],
                        font=("Segoe UI Symbol", max(10, int(size*.42)), "bold")
                    )
                elif cell["revealed"] and cell["number"]:
                    self.canvas.create_text(
                        (x1+x2)/2, (y1+y2)/2,
                        text=str(cell["number"]),
                        fill=number_colors[cell["number"]],
                        font=("Segoe UI", max(10, int(size*.36)), "bold")
                    )

                if self.hint_cell == (r, c):
                    self.canvas.create_rectangle(
                        x1+3, y1+3, x2-3, y2-3,
                        outline=self.theme["gold"], width=3
                    )

        if self.state == "paused":
            self.overlay("PAUSED", "Press Space to resume", self.theme["accent"])
        elif self.state == "won":
            self.overlay("MISSION COMPLETE",
                         f"Time {self.elapsed:03d}s   •   XP earned",
                         self.theme["good"])
        elif self.state == "lost":
            self.overlay("SYSTEM FAILURE",
                         "Mine triggered   •   F2 for a new board",
                         self.theme["danger"])

        flags = sum(cell["flag"] for row in self.cells for cell in row)
        shown = self.elapsed
        if self.state == "running" and self.start_time:
            shown = int(time.monotonic() - self.start_time)

        if hasattr(self, "hud"):
            self.hud.config(
                text=f"💣 {self.mines-flags:03d}    ⏱ {shown:03d}s    "
                     f"◆ LV {self.profile['level']}    XP {self.profile['xp']}"
            )

    def overlay(self, title, subtitle, color):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_rectangle(0, 0, w, h, fill="#050914", outline="")
        self.canvas.create_text(
            w/2, h/2-30, text=title,
            fill=color, font=("Segoe UI", 30, "bold")
        )
        self.canvas.create_text(
            w/2, h/2+25, text=subtitle,
            fill=self.theme["text"], font=("Segoe UI", 11, "bold")
        )

    def tick(self):
        if self.state == "running" and hasattr(self, "canvas"):
            self.draw()
        self.root.after(100, self.tick)


def main():
    root = tk.Tk()
    app = Minesweeper(root)
    root.mainloop()


if __name__ == "__main__":
    main()
