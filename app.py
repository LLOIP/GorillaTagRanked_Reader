"""GTC Rank Presence - multi-profile Ranked World tracker with Discord RPC."""
import os, re, sys, json, time, threading, webbrowser, subprocess
from pathlib import Path
from urllib.parse import urlparse
from tkinter import Tk, StringVar, BooleanVar, Label, Button, Entry, Checkbutton, Frame, messagebox
from tkinter import ttk
import pystray
import psutil
try:
    from winotify import Notification, audio
except Exception:
    Notification = None
    audio = None
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageTk

try:
    from pypresence import Presence
except Exception:
    Presence = None

APP_NAME = "GTC Rank Presence"
DISCORD_SERVER_URL = "https://discord.com/servers/1076000755867205713"
DEFAULT_PROFILE = "https://rankedworld.com/player/1113996311981740153"
POLL_SECONDS = 90
RANKS = {
    "bronze": ("Bronze", "bronze.png"), "silver": ("Silver", "silver.png"),
    "gold": ("Gold", "gold.png"), "platinum": ("Platinum", "platinum.png"),
    "ruby": ("Ruby", "ruby.png"), "sapphire": ("Sapphire", "sapphire.png")
}
DEFAULTS = {"profile_url": DEFAULT_PROFILE, "discord_client_id": "", "presence_enabled": False,
            "startup_enabled": False, "steamvr_monitor_enabled": True, "poll_seconds": POLL_SECONDS,
            "asset_keys": {k: k for k in RANKS}}

def resource_path(name):
    """Resolve bundled assets in PyInstaller builds and normal Python runs."""
    candidates = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / name)
    app_root = Path(__file__).resolve().parent
    candidates.extend([
        app_root / name,
        Path(sys.executable).resolve().parent / name,
    ])

    # Compatibility fallback for packages that used the earlier logo filename.
    if name == "gtc_app.png":
        if bundle_root:
            candidates.append(Path(bundle_root) / "gtc_logo.png")
        candidates.extend([
            app_root / "gtc_logo.png",
            Path(sys.executable).resolve().parent / "gtc_logo.png",
        ])

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    # Return the expected bundled path so the caller can report a useful error.
    return candidates[0] if candidates else Path(name)

def config_path():
    if os.name == "nt" and os.environ.get("APPDATA"):
        folder = Path(os.environ["APPDATA"]) / "GTC Rank Presence"
    else:
        folder = Path.home() / ".gtc_rank_presence"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "config.json"

CONFIG_PATH = config_path()

def load_config():
    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        saved = {}
    result = DEFAULTS.copy()
    result.update(saved)
    result["asset_keys"] = {**DEFAULTS["asset_keys"], **saved.get("asset_keys", {})}
    return result

def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")

def normalize_profile_url(value):
    value = value.strip()
    if value.isdigit():
        value = f"https://rankedworld.com/player/{value}"
    elif value and not value.startswith(("https://", "http://")):
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or parsed.netloc.lower() not in ("rankedworld.com", "www.rankedworld.com"):
        raise ValueError("Enter a Ranked World profile URL or player ID.")
    match = re.fullmatch(r"/player/(\d+)/?", parsed.path)
    if not match:
        raise ValueError("Profile link must look like https://rankedworld.com/player/123456789")
    return f"https://rankedworld.com/player/{match.group(1)}"

def bracket_for(rank, division, supplied=None):
    if supplied:
        return supplied.upper()
    rank, div = rank.lower(), int(division or 1)
    if rank == "bronze" or (rank == "silver" and div <= 1): return "LOW"
    if rank == "silver" or (rank == "gold" and div <= 1): return "MID"
    if rank in ("gold", "platinum"): return "HIGH"
    return "TOP"

def parse_rank(html):
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    # Restrict parsing to Ranked section so Scrims rank is never mistaken for active rank.
    start = re.search(r"\bRanked\b", text, re.I)
    if not start:
        raise ValueError("Could not find the Ranked section on this profile.")
    section = text[start.end():]
    end = re.search(r"\bScrims\b", section, re.I)
    if end:
        section = section[:end.start()]
    match = re.search(r"\b(Bronze|Silver|Gold|Platinum|Ruby|Sapphire)\s*(\d+)?\s*/\s*(LOW|MID|HIGH|TOP)\b", section, re.I)
    if not match:
        raise ValueError("No supported active Ranked division was found on this profile.")
    rank, division, bracket = match.group(1), match.group(2) or "1", match.group(3)
    key = rank.lower()
    return {"rank": f"{rank.capitalize()} {division}", "rank_key": key,
            "division": division, "bracket": bracket_for(key, division, bracket)}

def fetch_rank(profile_url):
    response = requests.get(profile_url, headers={"User-Agent": "Mozilla/5.0 GTC-Rank-Presence/2.0"}, timeout=20)
    response.raise_for_status()
    return parse_rank(response.text)

def startup_file():
    return Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup/GTC Rank Presence.bat"

def set_startup(enabled):
    if os.name != "nt" or not os.environ.get("APPDATA"):
        raise RuntimeError("The automatic startup toggle is currently available on Windows.")
    target = startup_file()
    if enabled:
        target.parent.mkdir(parents=True, exist_ok=True)
        if getattr(sys, "frozen", False):
            command = f' start "" "{Path(sys.executable).resolve()}"'
        else:
            py = Path(sys.executable)
            pyw = py.with_name("pythonw.exe")
            command = f' start "" "{pyw if pyw.exists() else py}" "{Path(__file__).resolve()}"'
        target.write_text("@echo off\r\n" + command + "\r\n", encoding="utf-8")
    else:
        target.unlink(missing_ok=True)


STEAMVR_APP_ID = "250820"
STEAMVR_URI = f"steam://rungameid/{STEAMVR_APP_ID}"

def steamvr_running():
    """Return True when SteamVR's main server process is present."""
    try:
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if name == "vrserver.exe":
                return True
    except Exception:
        pass
    return False

def show_toast(title, message, button_label=None, button_uri=None):
    """Show a Windows toast. Toast action opens Steam's SteamVR app URI."""
    if Notification is None:
        return False
    try:
        toast = Notification(
            app_id="GTC Rank Presence",
            title=title,
            msg=message,
            duration="long"
        )
        if button_label and button_uri:
            toast.add_actions(label=button_label, launch=button_uri)
        if audio is not None:
            toast.set_audio(audio.Default, loop=False)
        toast.show()
        return True
    except Exception:
        return False

def rank_progress_score(result):
    order = ["bronze", "silver", "gold", "platinum", "ruby", "sapphire"]
    tier = order.index(result["rank_key"])
    try:
        division = int(result.get("division", 1))
    except Exception:
        division = 1
    # A lower division number is treated as a higher division within a tier.
    return tier * 100 - division

class GTCApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        try:
            self.root.iconbitmap(str(resource_path("gtc_app.ico")))
        except Exception:
            pass
        self.root.geometry("740x690")
        self.root.minsize(660, 650)
        self.root.configure(bg="#10131b")
        self.config = load_config()
        self.current = None
        self.rpc = None
        self.rpc_connected = False
        self.fetching = False
        self.icon_photo = None
        self.rpc_started_at = None
        self.tray_icon = None
        self.tray_thread = None
        self.allow_full_quit = False
        self.previous_rank = None
        self.steamvr_was_running = None
        self.steamvr_monitor_after_id = None
        self.steamvr_monitor_var = BooleanVar(value=self.config.get("steamvr_monitor_enabled", True))
        self.profile_var = StringVar(value=self.config.get("profile_url", DEFAULT_PROFILE))
        self.client_id_var = StringVar(value=self.config.get("discord_client_id", ""))
        self.presence_var = BooleanVar(value=self.config.get("presence_enabled", False))
        self.startup_var = BooleanVar(value=self.config.get("startup_enabled", False))
        self.status_var = StringVar(value="Enter a Ranked World profile and press Save profile.")
        self.rank_var = StringVar(value="—")
        self.bracket_var = StringVar(value="STARTS: —")
        self.player_var = StringVar(value="No profile loaded")
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(500, self.refresh)
        self.root.after(1500, self.monitor_steamvr)

    def panel(self, parent):
        return Frame(parent, bg="#171c29", highlightbackground="#2a3448", highlightthickness=1)

    def _build(self):
        Label(self.root, text="GTC RANK PRESENCE", bg="#10131b", fg="#f4f7ff", font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=24, pady=(20, 2))
        Label(self.root, text="Your Ranked World profile • automatic rank refresh • Discord activity", bg="#10131b", fg="#929db3", font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(0, 10))

        profile = self.panel(self.root); profile.pack(fill="x", padx=24, pady=7)
        Label(profile, text="YOUR RANKED WORLD PROFILE", bg="#171c29", fg="#f4f7ff", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(12, 6))
        self.profile_entry = Entry(profile, textvariable=self.profile_var, bg="#0f1420", fg="#f4f7ff", insertbackground="white", relief="flat", font=("Segoe UI", 10))
        self.profile_entry.pack(fill="x", padx=15, ipady=8)
        Label(profile, text="Paste your profile URL or enter your numeric player ID.", bg="#171c29", fg="#8e9bb0", font=("Segoe UI", 8)).pack(anchor="w", padx=15, pady=(5, 10))
        Button(profile, text="Save profile & refresh", command=self.save_profile, bg="#36bd91", fg="#07150f", activebackground="#54d9ad", relief="flat", font=("Segoe UI", 9, "bold"), padx=14, pady=8).pack(anchor="w", padx=15, pady=(0, 13))

        card = self.panel(self.root); card.pack(fill="x", padx=24, pady=7)
        row = Frame(card, bg="#171c29"); row.pack(fill="x", padx=17, pady=15)
        self.badge_label = Label(row, text="GTC", bg="#171c29", fg="#8290a8", font=("Segoe UI", 10, "bold"), width=12, height=6)
        self.badge_label.pack(side="left", padx=(0, 18))
        info = Frame(row, bg="#171c29"); info.pack(side="left", fill="both", expand=True)
        Label(info, text="ACTIVE RANK", bg="#171c29", fg="#8794aa", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        Label(info, textvariable=self.rank_var, bg="#171c29", fg="#ffffff", font=("Segoe UI", 24, "bold")).pack(anchor="w")
        Label(info, textvariable=self.bracket_var, bg="#171c29", fg="#42d3a1", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(2, 5))
        Label(info, textvariable=self.player_var, bg="#171c29", fg="#9ca8bd", font=("Segoe UI", 9)).pack(anchor="w")
        Button(info, text="Open profile", command=self.open_profile, bg="#29364d", fg="white", relief="flat", padx=12, pady=6).pack(anchor="w", pady=(9, 0))

        discord = self.panel(self.root); discord.pack(fill="x", padx=24, pady=7)
        Label(discord, text="DISCORD RICH PRESENCE", bg="#171c29", fg="#f4f7ff", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(12, 7))
        Label(discord, text="Activity title is fixed by the Discord application; rank is shown in the activity state.", bg="#171c29", fg="#8e9bb0", font=("Segoe UI", 8), wraplength=640).pack(anchor="w", padx=15, pady=(0, 5))
        line = Frame(discord, bg="#171c29"); line.pack(fill="x", padx=15)
        Label(line, text="Application ID", bg="#171c29", fg="#aeb8ca", font=("Segoe UI", 9)).pack(side="left")
        Entry(line, textvariable=self.client_id_var, bg="#0f1420", fg="#f4f7ff", insertbackground="white", relief="flat").pack(side="left", fill="x", expand=True, padx=(12, 0), ipady=7)
        Checkbutton(discord, text="Enable Discord Rich Presence", variable=self.presence_var, command=self.toggle_presence, bg="#171c29", fg="#e8edf8", selectcolor="#0f1420", activebackground="#171c29", activeforeground="white").pack(anchor="w", padx=12, pady=(8, 2))
        Checkbutton(discord, text="Start this app when Windows starts", variable=self.startup_var, command=self.toggle_startup, bg="#171c29", fg="#e8edf8", selectcolor="#0f1420", activebackground="#171c29", activeforeground="white").pack(anchor="w", padx=12, pady=(0, 11))
        Checkbutton(discord, text="Monitor SteamVR (rank-up + close notifications)", variable=self.steamvr_monitor_var, command=self.toggle_steamvr_monitor, bg="#171c29", fg="#e8edf8", selectcolor="#0f1420", activebackground="#171c29", activeforeground="white").pack(anchor="w", padx=12, pady=(0, 11))

        actions = Frame(self.root, bg="#10131b")
        actions.pack(fill="x", padx=24, pady=(7, 4))
        Button(actions, text="Save settings / connect Discord", command=self.save_settings, bg="#29364d", fg="white", activebackground="#354662", relief="flat", padx=15, pady=9).pack(side="left")
        Button(actions, text="🦍  GTC Discord", command=lambda: webbrowser.open(DISCORD_SERVER_URL), bg="#5865F2", fg="white", activebackground="#4752c4", relief="flat", padx=14, pady=9).pack(side="left", padx=(8, 0))
        self.quit_leaf_photo = ImageTk.PhotoImage(Image.open(resource_path("gtc_app.png")).convert("RGBA").resize((20, 20), Image.Resampling.LANCZOS))
        Button(actions, text="Full Quit", image=self.quit_leaf_photo, compound="left", command=self.full_quit, bg="#7c3442", fg="white", activebackground="#9a4051", relief="flat", padx=14, pady=9).pack(side="right")
        Label(self.root, text="( with love, pinko <3 )", bg="#10131b", fg="#8490a6", font=("Segoe UI", 9, "italic")).pack(anchor="w", padx=26, pady=(4, 0))
        Label(self.root, textvariable=self.status_var, bg="#10131b", fg="#8f9bb0", font=("Segoe UI", 9), anchor="w", wraplength=680).pack(fill="x", padx=26, pady=(8, 4))
        Label(self.root, text=f"Auto-refresh: every {POLL_SECONDS} seconds • SteamVR monitoring • Ranked World", bg="#10131b", fg="#59667c", font=("Segoe UI", 8)).pack(anchor="w", padx=26, pady=(0, 12))

    def save_profile(self):
        try:
            self.config["profile_url"] = normalize_profile_url(self.profile_var.get())
            self.profile_var.set(self.config["profile_url"])
            save_config(self.config)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Profile link", str(exc))

    def save_settings(self):
        self.config["discord_client_id"] = self.client_id_var.get().strip()
        self.config["presence_enabled"] = self.presence_var.get()
        self.config["startup_enabled"] = self.startup_var.get()
        self.config["steamvr_monitor_enabled"] = self.steamvr_monitor_var.get()
        try:
            self.config["profile_url"] = normalize_profile_url(self.profile_var.get())
            self.profile_var.set(self.config["profile_url"])
            save_config(self.config)
            self.refresh()
            if self.presence_var.get(): self.update_presence()
            else: self.disconnect_rpc()
        except Exception as exc:
            messagebox.showerror("Settings", str(exc))

    def toggle_presence(self):
        self.config["presence_enabled"] = self.presence_var.get(); save_config(self.config)
        if self.presence_var.get(): self.update_presence()
        else: self.disconnect_rpc(); self.status_var.set("Discord Rich Presence disabled.")

    def toggle_startup(self):
        try:
            set_startup(self.startup_var.get())
            self.config["startup_enabled"] = self.startup_var.get(); save_config(self.config)
            self.status_var.set("Windows startup setting updated.")
        except Exception as exc:
            self.startup_var.set(False); self.status_var.set(str(exc)); messagebox.showerror("Startup", str(exc))

    def toggle_steamvr_monitor(self):
        enabled = self.steamvr_monitor_var.get()
        self.config["steamvr_monitor_enabled"] = enabled
        save_config(self.config)
        if enabled:
            self.steamvr_was_running = steamvr_running()
            self.status_var.set("SteamVR monitoring enabled.")
        else:
            self.status_var.set("SteamVR monitoring disabled.")

    def monitor_steamvr(self):
        if self.steamvr_monitor_var.get():
            running = steamvr_running()
            if self.steamvr_was_running is None:
                # Establish a baseline so launching the app while SteamVR is closed
                # does not produce a false alarm.
                self.steamvr_was_running = running
            elif self.steamvr_was_running and not running:
                show_toast(
                    "SteamVR Has Closed!",
                    "Was this an accident? Press below to reopen Steam and SteamVR.",
                    "Reopen SteamVR",
                    STEAMVR_URI
                )
                self.status_var.set("SteamVR closed • notification sent.")
            self.steamvr_was_running = running
        self.steamvr_monitor_after_id = self.root.after(2500, self.monitor_steamvr)

    def open_profile(self):
        try: webbrowser.open(normalize_profile_url(self.profile_var.get()))
        except Exception as exc: messagebox.showerror("Profile", str(exc))

    def refresh(self):
        if self.fetching: return
        try: url = normalize_profile_url(self.profile_var.get())
        except Exception as exc:
            self.status_var.set(str(exc)); self.schedule_refresh(); return
        self.fetching = True
        self.status_var.set("Checking profile rank…")
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url):
        try:
            result = fetch_rank(url)
            self.root.after(0, lambda: self.rank_received(result, url))
        except Exception as exc:
            error_text = str(exc)
            self.root.after(0, lambda e=error_text: self.fetch_failed(e))

    def fetch_failed(self, error):
        self.fetching = False
        self.status_var.set("Rank refresh failed: " + error[:180])
        self.schedule_refresh()

    def rank_received(self, result, url):
        self.fetching = False
        old_rank = self.previous_rank
        self.current = result
        if old_rank is not None and rank_progress_score(result) > rank_progress_score(old_rank):
            show_toast(
                "GTC Rank Up!",
                f"Your Ranked World rank increased to {result['rank']} • {result['bracket']}."
            )
        self.previous_rank = result
        self.rank_var.set(result["rank"]); self.bracket_var.set("STARTS: " + result["bracket"])
        self.player_var.set(url)
        try:
            im = Image.open(resource_path(RANKS[result["rank_key"]][1])).convert("RGBA")
            im.thumbnail((112, 112), Image.Resampling.LANCZOS)
            self.icon_photo = ImageTk.PhotoImage(im); self.badge_label.configure(image=self.icon_photo, text="")
        except Exception:
            self.badge_label.configure(image="", text=result["rank_key"].upper())
        self.status_var.set(f"Updated {time.strftime('%I:%M:%S %p')} • {result['rank']} / {result['bracket']}")
        if self.presence_var.get():
            self.update_presence()
        self.schedule_refresh()

    def schedule_refresh(self):
        self.root.after(POLL_SECONDS * 1000, self.refresh)

    def update_presence(self):
        if not self.presence_var.get() or not self.current: return
        if Presence is None:
            self.status_var.set("Discord RPC package missing. Reinstall using requirements.txt."); return
        client_id = self.client_id_var.get().strip()
        if not client_id:
            self.status_var.set("Enter a Discord Application ID to enable Rich Presence."); return
        try:
            if not self.rpc_connected:
                self.rpc = Presence(client_id); self.rpc.connect(); self.rpc_connected = True
            key = self.config.get("asset_keys", {}).get(self.current["rank_key"], self.current["rank_key"])
            profile = normalize_profile_url(self.profile_var.get())
            if self.rpc_started_at is None:
                self.rpc_started_at = int(time.time())
            self.rpc.update(details="Playing: Gorilla Tag COMP",
                            state=f"{self.current['rank']} • {self.current['bracket']}",
                            start=self.rpc_started_at,
                            large_image=key, large_text=f"{self.current['rank']} • GTC",
                            buttons=[{"label": "View Ranked World profile", "url": profile}])
            self.status_var.set("Discord Rich Presence active • rank updates automatically.")
        except Exception as exc:
            self.disconnect_rpc(); self.status_var.set("Discord RPC error: " + str(exc)[:140])

    def disconnect_rpc(self):
        if self.rpc:
            try: self.rpc.clear(); self.rpc.close()
            except Exception: pass
        self.rpc = None; self.rpc_connected = False
        self.rpc_started_at = None

    def hide_to_tray(self):
        self.root.withdraw()
        if self.tray_icon is None:
            try:
                tray_image = Image.open(resource_path("gtc_app.png")).convert("RGBA")
                self.tray_icon = pystray.Icon(
                    "GTC Rank Presence", tray_image, "GTC Rank Presence",
                    menu=pystray.Menu(
                        pystray.MenuItem("Open GTC Rank Presence", lambda icon, item: self.root.after(0, self.restore_window), default=True),
                        pystray.MenuItem("Full Quit", lambda icon, item: self.root.after(0, self.full_quit))
                    )
                )
                self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
                self.tray_thread.start()
            except Exception as exc:
                self.root.deiconify()
                self.status_var.set("Could not create tray icon: " + str(exc)[:120])

    def restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def close(self):
        # Closing the window hides it; Discord Rich Presence keeps running.
        self.hide_to_tray()

    def full_quit(self):
        self.allow_full_quit = True
        if self.steamvr_monitor_after_id is not None:
            try:
                self.root.after_cancel(self.steamvr_monitor_after_id)
            except Exception:
                pass
        self.disconnect_rpc()
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self.root.destroy()

def main():
    root = Tk(); GTCApp(root); root.mainloop()

if __name__ == "__main__": main()
