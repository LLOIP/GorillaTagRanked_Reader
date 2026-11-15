# GTC Rank Presence

Windows app for tracking a Ranked World profile and displaying rank in Discord Rich Presence.

## Features
- Refreshes Ranked World every 90 seconds.
- Discord activity details: `Playing: Gorilla Tag COMP`.
- Rank/division/bracket shown as the activity state.
- Discord elapsed-time clock begins when Rich Presence first activates and persists through rank refreshes.
- Closing the window hides the app to the system tray; use **Full Quit** in the window or tray menu to exit and clear Rich Presence.
- GTC Discord shortcut and app credit: `( with love, pinko <3 )`.
- EXE icon uses the supplied blue pixelated leaf.

## Build
Run `build_windows.bat`, or push this repository to GitHub and use Actions → Build Windows EXE.

The Discord activity's application title (the small title above its details) is controlled by the Discord Developer Portal application name. Discord RPC cannot dynamically rename that title per user's rank; the rank is shown in the activity state instead.

## Discord server
The shortcut opens the GTC | VR Esports Discord server listing:
https://discord.com/servers/1076000755867205713


## SteamVR monitoring and notifications

Enable **Monitor SteamVR** in the app to receive Windows desktop notifications when:
- Ranked World rank progresses upward after a refresh.
- SteamVR closes after it was detected running.

The SteamVR notification includes a **Reopen SteamVR** action. Selecting it opens Steam's
SteamVR launch link (`steam://rungameid/250820`), which asks Steam to start SteamVR.
Discord Rich Presence connects automatically on launch when it is enabled in saved settings
and a Discord Application ID has been configured. A Discord application must be created once
in the Discord Developer Portal; the app cannot create Discord applications on a user's behalf.


### Fixed missing logo asset in packaged EXE

The app now resolves bundled assets from the PyInstaller extraction folder, the app folder,
or the legacy `gtc_logo.png` name. The GitHub Actions build also checks that the required
logo and rank images exist before packaging and includes both logo filenames.


### Active rank in Discord

Rich Presence now puts the player's current rank directly in the activity details
(`Active Rank: Ruby 2`, for example) and shows the GTC COMP bracket in the state.
The Discord application's own title is controlled by Discord Developer Portal and is
not dynamically editable by Rich Presence.
