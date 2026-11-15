"""
GTC Rank Presence
A small Windows desktop app that reads the Ranked World player page,
shows the current Ranked division with your supplied badge icons, and
optionally publishes Discord Rich Presence.

Install:
    py -m pip install -r requirements.txt
Run:
    py app.py
"""
import os
import re
import sys
import json
import time
import threading
import subprocess
import webbrowser
from pathlib import Path
from tkinter import Tk, StringVar, BooleanVar, Label, Button, Entry, Checkbutton, Frame, messagebox
from tkinter import ttk

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageTk

try:
    from pypresence import Presence
except Exception:
    Presence = None

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
PLAYER_URL = "https://rankedworld.com/player/1113996311981740153"
POLL_SECONDS = 90
RANKS = {
    "bronze": ("Bronze", "bronze.png", "LOW"),
    "silver": ("Silver", "silver.png", "LOW"),
    "gold": ("Gold", "gold.png", "MID"),
    "platinum": ("Platinum", "platinum.png", "HIGH"),
    "ruby": ("Ruby", "ruby.png", "TOP"),
    "sapphire": ("Sapphire", "sapphire.png", "TOP"),
}
RANK_RE = re.compile(
    r"\b(Bronze|Silver|Gold|Platinum|Ruby|Sapphire)\s*(\d+)?\s*(?:/|•|-)\s*(LOW|MID|HIGH|TOP)\b",
    re.I
)
DIVISION_RE = re.compile(r"\b(Bronze|Silver|Gold|Platinum|Ruby|Sapphire)\s*(\d+)\b", re.I)

DEFAULTS = {
    "discord_client_id": "",
    "presence_enabled": False,
    "startup_enabled": False,
    "poll_seconds": POLL_SECONDS,
    "asset_keys": {
        "bronze": "bronze", "silver": "silver", "gold": "gold",
        "platinum": "platinum", "ruby": "ruby", "sapphire": "sapphire"
    }
}

def load_config():
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        merged = DEFAULTS.copy()
        merged.update(data)
        keys = DEFAULTS["asset_keys"].copy()
        keys.update(data.get("asset_keys", {}))
        merged["asset_keys"] = keys
        return merged
    except Exception:
        return DEFAULTS.copy()

def save_config(data):
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def bracket_for(rank, division, site_bracket=None):
    if site_bracket:
        return site_bracket.upper()
    rank = rank.lower()
    div = int(division or 1)
    # User's requested bracket ranges. Silver 2 is treated as MID (the
    # boundary between LOW and MID); Gold 2 begins HIGH.
    if rank == "bronze" or (rank == "silver" and div <= 1):
        return "LOW"
    if rank == "silver" or (rank == "gold" and div <= 1):
        return "MID"
    if rank in ("gold", "platinum"):
        return "HIGH"
    return "TOP"

def parse_rank(html):
    soup = BeautifulSoup(html, "html.parser")
    # Prefer the Ranked section: the page can also contain a separate Scrims rank.
    ranked_heading = None
    for node in soup.find_all(["h1", "h2", "h3", "h4"]):
        if node.get_text(" ", strip=True).lower() == "ranked":
            ranked_heading = node
            break

    if ranked_heading:
        chunks = []
        for sibling in ranked_heading.find_all_next(limit=45):
            if sibling.name in ("h1", "h2", "h3", "h4") and sibling is not ranked_heading:
                break
            txt = sibling.get_text(" ", strip=True)
            if txt:
                chunks.append(txt)
        section_text = " ".join(chunks)
    else:
        plain = soup.get_text(" ", strip=True)
        pos = plain.lower().find("ranked")
        section_text = plain[pos:pos+900] if pos >= 0 else plain

    # Ranked World commonly presents "Ruby 2 / TOP" or "Ruby 2 / TOP".
    match = RANK_RE.search(section_text)
    if not match:
        # fallback: identify division in ranked section, then infer bracket
        match = DIVISION_RE.search(section_text)
        if not match:
            raise ValueError("Could not find a Ranked division on the profile page.")
        rank, division = match.group(1), match.group(2)
        site_bracket = None
    else:
        rank, division, site_bracket = match.group(1), match.group(2) or "1", match.group(3)

    rank_key = rank.lower()
    display = rank.capitalize() + (f" {division}" if division else "")
    bracket = bracket_for(rank, division, site_bracket)
    return {"rank": display, "rank_key": rank_key, "division": division or "1", "bracket": bracket}

def fetch_rank():
    headers = {"User-Agent": "GTC-Rank-Presence/1.0 (profile display)"}
    response = requests.get(PLAYER_URL, headers=headers, timeout=15)
    response.raise_for_status()
    return parse_rank(response.text)

def startup_batch_path():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("Windows Startup folder is not available.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "GTC Rank Presence.bat"

def set_startup(enabled):
    if os.name != "nt":
        raise RuntimeError("The PC startup option is currently supported on Windows only.")
    target = startup_batch_path()
    if enabled:
        python = Path(sys.executable)
        pythonw = python.with_name("pythonw.exe")
        runner = pythonw if pythonw.exists() else python
        script = Path(__file__).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'@echo off\r\nstart "" "{runner}" "{script}"\r\n', encoding="utf-8")
    else:
        try:
            target.unlink()
        except FileNotFoundError:
            pass

class GTCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GTC • Rank Presence")
        self.root.geometry("720x570")
        self.root.minsize(650, 520)
        self.root.configure(bg="#10131b")
        self.config = load_config()
        self.current = None
        self.rpc = None
        self.rpc_connected = False
        self.stop_event = threading.Event()
        self.fetching = False
        self.icon_photo = None

        self.client_id_var = StringVar(value=self.config.get("discord_client_id", ""))
        self.presence_var = BooleanVar(value=self.config.get("presence_enabled", False))
        self.startup_var = BooleanVar(value=self.config.get("startup_enabled", False))
        self.status_var = StringVar(value="Waiting for first rank check…")
        self.rank_var = StringVar(value="—")
        self.bracket_var = StringVar(value="—")
        self.name_var = StringVar(value="Ranked World player 1113996311981740153")

        self._style()
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(400, self.refresh)
        self.root.after(1500, self.background_loop)

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor="#202637", background="#42d3a1")
        style.configure("TCheckbutton", background="#171c29", foreground="#e8edf8")
        style.map("TCheckbutton", background=[("active", "#171c29")], foreground=[("active", "#ffffff")])

    def _build(self):
        header = Frame(self.root, bg="#10131b")
        header.pack(fill="x", padx=24, pady=(20, 8))
        Label(header, text="GTC RANK PRESENCE", bg="#10131b", fg="#f4f7ff",
              font=("Segoe UI", 19, "bold")).pack(anchor="w")
        Label(header, text="Live Ranked World rank • Discord Rich Presence",
              bg="#10131b", fg="#929db3", font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))

        card = Frame(self.root, bg="#171c29", highlightbackground="#2a3448", highlightthickness=1)
        card.pack(fill="x", padx=24, pady=12)
        left = Frame(card, bg="#171c29")
        left.pack(side="left", padx=18, pady=18)
        self.badge_label = Label(left, text="GTC", bg="#171c29", fg="#8290a8",
                                 font=("Segoe UI", 10, "bold"), width=12, height=6)
        self.badge_label.pack()
        right = Frame(card, bg="#171c29")
        right.pack(side="left", fill="both", expand=True, padx=(8, 18), pady=18)
        Label(right, text="ACTIVE RANK", bg="#171c29", fg="#8794aa",
              font=("Segoe UI", 9, "bold")).pack(anchor="w")
        Label(right, textvariable=self.rank_var, bg="#171c29", fg="#ffffff",
              font=("Segoe UI", 24, "bold")).pack(anchor="w", pady=(2, 0))
        Label(right, textvariable=self.bracket_var, bg="#171c29", fg="#42d3a1",
              font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(3, 8))
        Label(right, textvariable=self.name_var, bg="#171c29", fg="#9ca8bd",
              font=("Segoe UI", 9)).pack(anchor="w")
        Button(right, text="Open Ranked World profile", command=lambda: webbrowser.open(PLAYER_URL),
               bg="#29364d", fg="white", activebackground="#354662", activeforeground="white",
               relief="flat", padx=12, pady=7, cursor="hand2").pack(anchor="w", pady=(12, 0))

        settings = Frame(self.root, bg="#171c29", highlightbackground="#2a3448", highlightthickness=1)
        settings.pack(fill="x", padx=24, pady=8)
        Label(settings, text="DISCORD CONNECTION", bg="#171c29", fg="#f4f7ff",
              font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        row = Frame(settings, bg="#171c29")
        row.pack(fill="x", padx=16)
        Label(row, text="Application ID", bg="#171c29", fg="#aeb8ca",
              font=("Segoe UI", 9)).pack(side="left")
        self.client_entry = Entry(row, textvariable=self.client_id_var, bg="#0f1420", fg="#f4f7ff",
                                  insertbackground="white", relief="flat", font=("Segoe UI", 10))
        self.client_entry.pack(side="left", fill="x", expand=True, padx=(12, 0), ipady=7)
        Checkbutton(settings, text="Enable Discord Rich Presence", variable=self.presence_var,
                    command=self.toggle_presence, bg="#171c29", fg="#e8edf8",
                    selectcolor="#0f1420", activebackground="#171c29",
                    activeforeground="white").pack(anchor="w", padx=13, pady=(10, 3))
        Checkbutton(settings, text="Start this app when Windows starts", variable=self.startup_var,
                    command=self.toggle_startup, bg="#171c29", fg="#e8edf8",
                    selectcolor="#0f1420", activebackground="#171c29",
                    activeforeground="white").pack(anchor="w", padx=13, pady=(0, 12))

        bottom = Frame(self.root, bg="#10131b")
        bottom.pack(fill="x", padx=24, pady=(8, 0))
        Button(bottom, text="Save / Connect", command=self.save_and_connect,
               bg="#36bd91", fg="#07150f", activebackground="#54d9ad",
               relief="flat", font=("Segoe UI", 9, "bold"), padx=15, pady=9).pack(side="left")
        Button(bottom, text="Refresh rank", command=self.refresh,
               bg="#29364d", fg="white", activebackground="#354662",
               relief="flat", padx=15, pady=9).pack(side="left", padx=8)
        Label(self.root, textvariable=self.status_var, bg="#10131b", fg="#8f9bb0",
              font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=26, pady=(13, 5))
        Label(self.root, text="Rank source: Ranked World • Refreshes every 90 seconds",
              bg="#10131b", fg="#59667c", font=("Segoe UI", 8)).pack(anchor="w", padx=26, pady=(0, 14))

    def save_and_connect(self):
        self.config["discord_client_id"] = self.client_id_var.get().strip()
        self.config["presence_enabled"] = self.presence_var.get()
        self.config["startup_enabled"] = self.startup_var.get()
        save_config(self.config)
        self.update_presence()
        self.status_var.set("Settings saved. " + ("Discord presence connected." if self.rpc_connected else "Check Discord and your Application ID."))

    def toggle_presence(self):
        self.config["presence_enabled"] = self.presence_var.get()
        save_config(self.config)
        if self.presence_var.get():
            self.update_presence()
        else:
            self.disconnect_rpc()
            self.status_var.set("Discord Rich Presence disabled.")

    def toggle_startup(self):
        try:
            set_startup(self.startup_var.get())
            self.config["startup_enabled"] = self.startup_var.get()
            save_config(self.config)
            self.status_var.set("Windows startup setting updated.")
        except Exception as exc:
            self.startup_var.set(False)
            self.status_var.set(str(exc))
            messagebox.showerror("Startup option", str(exc))

    def refresh(self):
        if self.fetching:
            return
        self.fetching = True
        self.status_var.set("Checking Ranked World…")
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self):
        try:
            result = fetch_rank()
            self.root.after(0, lambda r=result: self._rank_received(r))
        except Exception as exc:
            self.root.after(0, lambda e=str(exc): self._fetch_failed(e))

    def _fetch_failed(self, error):
        self.fetching = False
        self.status_var.set("Could not refresh rank: " + error[:150])

    def _rank_received(self, result):
        self.fetching = False
        self.current = result
        self.rank_var.set(result["rank"])
        self.bracket_var.set("STARTS: " + result["bracket"])
        self.name_var.set("Ranked World • pinkofrr")
        icon_path = APP_DIR / RANKS[result["rank_key"]][1]
        try:
            image = Image.open(icon_path).convert("RGBA")
            image.thumbnail((112, 112), Image.Resampling.LANCZOS)
            self.icon_photo = ImageTk.PhotoImage(image)
            self.badge_label.configure(image=self.icon_photo, text="")
        except Exception:
            self.badge_label.configure(image="", text=result["rank_key"].upper())
        self.status_var.set(f"Updated: {time.strftime('%I:%M:%S %p')} • {result['rank']} / {result['bracket']}")
        if self.presence_var.get():
            self.update_presence()

    def background_loop(self):
        if self.current is not None and not self.fetching:
            # Refresh periodically without blocking the window.
            pass
        self.root.after(POLL_SECONDS * 1000, self.refresh)
        self.root.after(POLL_SECONDS * 1000 + 1000, self.background_loop)

    def update_presence(self):
        if not self.presence_var.get() or not self.current:
            return
        if Presence is None:
            self.status_var.set("Install dependencies first: pip install -r requirements.txt")
            return
        client_id = self.client_id_var.get().strip()
        if not client_id:
            self.status_var.set("Enter your Discord Application ID to enable Rich Presence.")
            return
        try:
            if not self.rpc_connected:
                self.rpc = Presence(client_id)
                self.rpc.connect()
                self.rpc_connected = True
            key = self.config.get("asset_keys", {}).get(self.current["rank_key"], self.current["rank_key"])
            self.rpc.update(
                details="Playing: GTC",
                state=f"{self.current['rank']} • {self.current['bracket']}",
                large_image=key,
                large_text=f"{self.current['rank']} • GTC",
                buttons=[{"label": "View Ranked World profile", "url": PLAYER_URL}]
            )
            self.status_var.set("Discord Rich Presence is active.")
        except Exception as exc:
            self.disconnect_rpc()
            self.status_var.set("Discord RPC error: " + str(exc)[:130])

    def disconnect_rpc(self):
        if self.rpc:
            try:
                self.rpc.clear()
                self.rpc.close()
            except Exception:
                pass
        self.rpc = None
        self.rpc_connected = False

    def close(self):
        self.stop_event.set()
        self.disconnect_rpc()
        self.root.destroy()

def main():
    root = Tk()
    GTCApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
