#!/bin/bash

echo "Marcel Location Simulator - macOS Build Script"
echo "Created by Marcel Afsar"
echo ""

# Activate virtual environment
if [ -f venv/bin/activate ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo ""

# Build with PyInstaller
echo "Building premium application..."
pyinstaller --onefile \
    --windowed \
    --name "Marcel-Location-Simulator" \
    --add-data "config.yaml:." \
    --add-data "src/gui/map_template.html:src/gui" \
    --add-data "src/gui/style.qss:src/gui" \
    --hidden-import=pymobiledevice3 \
    --hidden-import=PyQt6 \
    --hidden-import=PyQt6.QtCore \
    --hidden-import=PyQt6.QtGui \
    --hidden-import=PyQt6.QtWidgets \
    --hidden-import=PyQt6.QtWebEngineWidgets \
    --hidden-import=PyQt6.QtWebEngineCore \
    --hidden-import=sqlalchemy \
    --hidden-import=sqlalchemy.sql.default_comparator \
    --hidden-import=loguru \
    --hidden-import=yaml \
    --hidden-import=requests \
    src/main.py

echo ""
echo "Build complete!"
echo "Application location: dist/Marcel-Location-Simulator.app"