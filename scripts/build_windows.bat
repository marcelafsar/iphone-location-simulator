@echo off
echo Marcel Location Simulator - Windows Build Script
echo Created by Marcel Afsar
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Build with PyInstaller
echo Building premium executable...
pyinstaller --onefile ^
    --windowed ^
    --name "Marcel-Location-Simulator" ^
    --add-data "config.yaml;." ^
    --add-data "src/gui/map_template.html;src/gui" ^
    --add-data "src/gui/style.qss;src/gui" ^
    --hidden-import=pymobiledevice3 ^
    --hidden-import=PyQt6 ^
    --hidden-import=PyQt6.QtCore ^
    --hidden-import=PyQt6.QtGui ^
    --hidden-import=PyQt6.QtWidgets ^
    --hidden-import=PyQt6.QtWebEngineWidgets ^
    --hidden-import=PyQt6.QtWebEngineCore ^
    --hidden-import=sqlalchemy ^
    --hidden-import=sqlalchemy.sql.default_comparator ^
    --hidden-import=loguru ^
    --hidden-import=yaml ^
    --hidden-import=requests ^
    src/main.py

echo.
echo Build complete!
echo Executable location: dist\Marcel-Location-Simulator.exe
pause