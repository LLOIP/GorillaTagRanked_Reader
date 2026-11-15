# GTC Rank Presence

Windows desktop app that displays the active **Ranked** division from the supplied Ranked World player profile and can publish Discord Rich Presence.

## Install and run
1. Install Python 3.10 or newer from https://www.python.org/downloads/ (enable **Add Python to PATH**).
2. Extract this folder somewhere permanent, such as `Documents\GTC Rank Presence`.
3. Open Command Prompt in this folder and run:
   ```
   py -m pip install -r requirements.txt
   py app.py
   ```

## Discord Rich Presence setup
Rich Presence is published to the Discord account currently signed in to the **Discord desktop app** on this PC. This app does not ask for your Discord password and does not sign in to or switch Discord accounts.

1. Open the Discord Developer Portal: https://discord.com/developers/applications
2. Create a New Application (name it `GTC` or another name you prefer).
3. Copy its **Application ID**.
4. Open **Rich Presence → Art Assets** for that application.
5. Upload the six supplied PNG icons there. Use these exact asset keys (lowercase):
   - `bronze`
   - `silver`
   - `gold`
   - `platinum`
   - `ruby`
   - `sapphire`
6. Keep the Discord desktop app open and signed in.
7. In GTC Rank Presence, paste the Application ID, tick **Enable Discord Rich Presence**, then click **Save / Connect**.

Discord presence text:
- Details: `Playing: GTC`
- State: current division and bracket, e.g. `Ruby 2 • TOP`
- The presence button opens the Ranked World profile.

Note: Discord RPC images must be uploaded as Rich Presence assets to your Discord application. The local PNG files are used in this desktop app; Discord cannot display a local disk image directly.

## Windows startup
Tick **Start this app when Windows starts**. The app creates a small `.bat` shortcut in your Windows Startup folder. Untick it to remove the shortcut. Keep the extracted app folder in the same place.

## Rank brackets
The app reads the **Ranked** section (not the separate Scrims section). It uses the bracket shown on the profile when available. Fallback bracket mapping follows:
- Bronze and Silver 1: LOW
- Silver 2 and Silver 3: MID
- Gold 1: MID
- Gold 2 and Platinum: HIGH
- Ruby and Sapphire: TOP

The source page may change its layout or restrict automated requests. If that happens, the app will show a refresh error rather than invent a rank. Refresh interval is 90 seconds.

## Files
- `app.py` — complete Python application
- `requirements.txt` — Python packages
- `config.json` — created automatically for local settings
- `*.png` — your supplied rank icons
