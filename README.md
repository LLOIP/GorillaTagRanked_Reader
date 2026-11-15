# GTC Rank Presence

A multi-user desktop app: each person enters their own Ranked World player URL or numeric player ID. The app saves that profile locally, reads its **Ranked** section (not Scrims), updates the badge and Discord Rich Presence, and checks again every 90 seconds.

## Build the Windows EXE with GitHub Actions (no local Python/build setup)

1. Create a GitHub account if you do not already have one.
2. Create a **new public or private repository** on GitHub.
3. Upload the contents of this folder to the repository. Make sure `.github/workflows/build-windows.yml` is included. (When uploading through the website, GitHub may hide dot-folders; if so, upload using GitHub Desktop or `git` so the `.github` folder is preserved.)
4. Open the repository's **Actions** tab and enable Actions if GitHub asks.
5. Select **Build Windows EXE** in the left sidebar.
6. Click **Run workflow** → **Run workflow**.
7. Wait for the green check mark, open the completed workflow run, and scroll to **Artifacts**.
8. Download **GTC-Rank-Presence-Windows**. Extract it and run `GTC Rank Presence.exe` on Windows.

The workflow builds a **standalone, single-file Windows executable** on a GitHub-hosted Windows runner. End users do not need Python installed. Windows SmartScreen may show an unknown-publisher warning because the EXE is not code-signed; only run builds from your own trusted repository.

### Build automatically

The same workflow also runs whenever you push commits to `main` or `master`. To publish a downloadable GitHub Release, create and push a version tag, for example:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow will attach `GTC Rank Presence.exe` to that GitHub Release.

## Optional local build on Windows

If you prefer building locally, install Python 3.10+ and run `build_windows.bat`. That produces an executable folder under `dist`.

## Add your own Ranked World profile

1. Copy your profile link, such as `https://rankedworld.com/player/123456789`.
2. Paste it into **Your Ranked World Profile**. You can also enter only the numeric player ID.
3. Click **Save profile & refresh**.
4. Your rank icon, division, bracket and Discord activity will refresh automatically every 90 seconds. Your profile link is saved on your own computer.

## Discord Rich Presence

Rich Presence appears on the Discord account currently signed in to the Discord desktop app on that computer. The app never asks for Discord passwords or tokens.

For a shared public release, the app publisher should create one Discord Developer Application, upload the six rank PNGs in **Rich Presence → Art Assets**, and distribute that same Application ID to users. The required image keys are `bronze`, `silver`, `gold`, `platinum`, `ruby`, and `sapphire`. Enter the Application ID, keep Discord desktop running, enable Rich Presence, and click **Save settings / connect Discord**.

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
- `.github/workflows/build-windows.yml` — automatic GitHub Actions EXE build
- `build_windows.bat` — optional local Windows build
- `requirements.txt` — Python dependencies and PyInstaller
- six rank badge PNGs, `gtc_logo.png`, and `gtc_app.ico`
