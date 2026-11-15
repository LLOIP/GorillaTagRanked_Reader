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
