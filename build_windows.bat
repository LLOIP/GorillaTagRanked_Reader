@echo off
setlocal
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 goto error
py -m PyInstaller --noconfirm --clean --windowed --onedir --name "GTC Rank Presence" --icon "gtc_app.ico" --add-data "bronze.png;." --add-data "silver.png;." --add-data "gold.png;." --add-data "platinum.png;." --add-data "ruby.png;." --add-data "sapphire.png;." --add-data "gtc_logo.png;." --add-data "gtc_app.ico;." app.py
if errorlevel 1 goto error
echo.
echo Build complete: dist\GTC Rank Presence\GTC Rank Presence.exe
pause
exit /b 0
:error
echo Build failed. Check the messages above.
pause
exit /b 1
