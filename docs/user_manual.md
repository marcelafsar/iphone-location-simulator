# Marcel Location Simulator - User Manual

## Table of Contents
1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [First-Time Setup](#first-time-setup)
5. [Basic Usage](#basic-usage)
6. [Advanced Features](#advanced-features)
7. [Troubleshooting](#troubleshooting)
8. [Frequently Asked Questions (FAQ)](#faq)

---

<a name="introduction"></a>
## 1. Introduction
**Marcel Location Simulator** is a premium, high-performance desktop application designed for Windows to easily spoof and simulate GPS coordinates on Apple iPhones. Developed for developers, testers, and advanced users, it offers precise manual controls (using D-PAD/WASD keyboards) and realistic route simulations including simulated traffic stops.

> [!WARNING]
> This tool is intended for educational, testing, and development purposes only. Using location-spoofing utilities may violate the terms of service of various location-based applications.

---

<a name="system-requirements"></a>
## 2. System Requirements
- **Operating System:** Windows 10 or 11 (64-bit)
- **Python:** Version 3.9 or higher (if running from source)
- **Frameworks:** PyQt6, PyQt6-WebEngine
- **Device Support:** iOS 16, 17, 18+ (iPhones)
- **Connection:** USB-A/C to Lightning or USB-C cable (MFi-certified highly recommended)

---

<a name="installation"></a>
## 3. Installation

### Option A: Running from Source (Development Mode)
1. **Prepare Python Environment:**
   Ensure Python 3.9+ is installed and added to your system PATH.
2. **Install Dependencies:**
   Install required libraries using standard package manager:
   ```cmd
   pip install -r requirements.txt
   ```
3. **Launch the App:**
   Start the application directly from python:
   ```cmd
   python src/main.py
   ```

### Option B: Pre-packaged Executable (.exe)
1. Unzip the release bundle.
2. Run `Marcel-Location-Simulator.exe` with Administrator privileges (required for RSD tunnel daemon operations).

---

<a name="first-time-setup"></a>
## 4. First-Time Setup

### 1. Enable Developer Mode on iPhone
To allow GPS simulation, Developer Mode must be turned on:
1. Open **Settings** on your iPhone.
2. Navigate to **Privacy & Security** > scroll to the bottom and select **Developer Mode**.
3. Toggle **Developer Mode** to **ON**.
4. Restart your iPhone when prompted.
5. After reboot, unlock your iPhone and tap **Turn On** to confirm, then enter your passcode.

### 2. Establish PC Trust Relation
1. Connect your iPhone to your PC using a reliable USB cable.
2. Unlock your iPhone screen.
3. Tap **Trust This Computer** when prompted on your screen.
4. Enter your iPhone passcode to confirm the connection.

---

<a name="basic-usage"></a>
## 5. Basic Usage

### 1. Connecting Your Device
- Open **Marcel Location Simulator**.
- Click the **Connect** button in the floating top-left device bar.
- The status bar will change to **Connected** and show your iPhone's name, model, iOS version, and current battery level.

### 2. Teleporting to Coordinates
- **Manual Input:** Enter the desired latitude and longitude in the **Coordinates** box on the floating sidebar, then click **Teleport Here**.
- **Interactive Map:** Simply click anywhere on the dark-mode Leaflet map, and the coordinates will automatically update. Click **Teleport Here** to teleport.
- **Search Box:** Type a destination name (e.g. "Times Square", "Tokyo Tower") into the search input and hit enter to automatically pan to the location.

### 3. Route Simulation
To simulate traveling between two coordinates:
1. Select a start location (your current teleported coordinates).
2. Set the destination by typing the coordinates into the **Route Simulation** sidebar fields or by picking on the map.
3. Choose a movement mode preset (Walking, Cycling, Driving) or slide the **Speed** slider to a custom value (supports up to 100 km/h).
4. Check **Simulate traffic lights & stop signs** if you want realistic stops (pauses the journey dynamically at 30% and 70% of the route for 6–12 seconds).
5. Click **Start Route** to begin. The map will display a blue route path and show real-time progress.

### 4. Joystick Control
- Use the **Joystick** buttons in the panel or use your keyboard's **WASD** / **Arrow** keys to make fine adjustments to your position.
- Keyboard focus must be on the main application window to use keyboard hotkeys.
- Movement step size scales automatically based on the speed slider setting.

---

<a name="advanced-features"></a>
## 6. Advanced Features

### Saved Favorites
- Keep a list of your most visited coordinates!
- Click the dialog menu to add, edit, category tag, or delete saved locations.
- Double-click any saved location to immediately teleport to it.

---

<a name="troubleshooting"></a>
## 7. Troubleshooting

### Connection Fails / "Device Not Connected"
- **Developer Mode:** Ensure it is definitely ON. Some iOS updates turn it off automatically.
- **Administrator Privileges:** Run the application or terminal command as **Administrator** so the background `tunneld` process can mount developer images and setup virtual networking tunnels.
- **RSD Tunnel Problems:** If `pymobiledevice3 remote tunneld` cannot start, make sure no other location simulator (e.g. 3utools, Xcode) is running in the background.

### Spoofed Location Does Not Revert
- To restore your actual GPS location, click the **Reset GPS** button in the application.
- If it still remains, disconnect the USB cable and restart your iPhone to reset the system location database cache.

---

<a name="faq"></a>
## 8. Frequently Asked Questions (FAQ)

**Q: Do I need an internet connection?**  
A: Yes, an active internet connection is required to load map tiles and search coordinates via OpenStreetMap Nominatim.

**Q: Does this save my location simulation permanently?**  
A: No. GPS spoofing is active only as long as simulated in the application. Clearing the simulation restores real coordinates.

---
**Created by Marcel Afsar.**  
*Last updated: 2026. Version: 1.0.0*
