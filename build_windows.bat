@echo off
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "GTC Rank Presence" --icon "gtc_app.ico" --add-data "bronze.png;." --add-data "silver.png;." --add-data "gold.png;." --add-data "platinum.png;." --add-data "ruby.png;." --add-data "sapphire.png;." --add-data "gtc_app.png;." app.py
pause
