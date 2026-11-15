# GTC Rank Presence

A multi-user desktop app: each person enters their own Ranked World player URL or numeric player ID. The app saves that profile locally, reads its **Ranked** section (not Scrims), updates the badge and Discord Rich Presence, and checks again every 90 seconds.

## Easiest way for Windows users (no Python needed)
A Windows `.exe` can be built from this project using `build_windows.bat` on a Windows PC:
1. Install Python 3.10+ and enable **Add Python to PATH**.
2. Extract this folder.
3. Double-click `build_windows.bat` and wait for it to finish.
4. Share the entire `dist\GTC Rank Presence` folder. Users run `GTC Rank Presence.exe` inside it. Keep the folder together because it contains the badge assets.

This build script must be run on Windows to create the Windows executable. The source app can also run on other desktop systems that have Python and Tk support installed:

```bash
python -m pip install -r requirements.txt
python app.py
```

## Add your own Ranked World profile
1. Copy your profile link, such as `https://rankedworld.com/player/123456789`.
2. Paste it into **Your Ranked World Profile**. You can also enter only the numeric player ID.
3. Click **Save profile & refresh**.
4. Your rank icon, division, bracket and Discord activity will refresh automatically every 90 seconds. Your profile link is saved on your own computer.

## Discord Rich Presence
Rich Presence appears on the Discord account currently signed in to the Discord desktop app on that computer. The app never asks for Discord passwords or tokens.

For a shared public release, the app publisher should create one Discord Developer Application, upload the six rank PNGs in **Rich Presence → Art Assets**, and distribute that same Application ID to users. The required image keys are `bronze`, `silver`, `gold`, `platinum`, `ruby`, and `sapphire`. If users build their own copy, they can create their own Discord application and upload the assets themselves.

Enter the Application ID, keep Discord desktop running, enable Rich Presence, and click **Save settings / connect Discord**.

Presence fields:
- Details: `Playing: GTC`
- State: current division and bracket (for example `Ruby 2 • TOP`)
- Large image: current rank badge
- Button: opens the profile currently entered in the app

## Windows startup
Tick **Start this app when Windows starts**. It creates a shortcut script in the current Windows user's Startup folder. Untick it to remove it. Keep the app folder in the same location after enabling startup.

## Bracket behavior
The app uses the bracket shown in the profile's Ranked section. Fallback mapping, if the site omits a bracket, is: Bronze/Silver 1 = LOW; Silver 2+ and Gold 1 = MID; Gold 2/Platinum = HIGH; Ruby/Sapphire = TOP.

The app reads the public profile page. If Ranked World changes its page structure, blocks requests, or the profile is private/unavailable, the app reports a refresh error instead of guessing a rank.

## Included files
- `app.py` — desktop application
- `build_windows.bat` — builds a Windows app folder containing the executable
- `requirements.txt` — Python dependencies and PyInstaller
- `bronze.png`, `silver.png`, `gold.png`, `platinum.png`, `ruby.png`, `sapphire.png` — supplied rank badges


## GTC Ranked League logo
The supplied-reference-inspired logo is included as `gtc_logo.png`.
The Windows icon file is `gtc_app.ico`; the build script applies it to the executable.
