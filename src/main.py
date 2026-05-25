"""
Marcel Location Simulator
Premium iPhone GPS Location Simulator for Windows
Created by Marcel Afsar
"""

import sys
import os
import atexit
import signal
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import setup_logger
from utils.config_manager import ConfigManager
from gui.main_window import MainWindow


# Global reference so atexit/signal handlers can reach it
_main_window = None


def _cleanup_orphan_processes():
    """
    Kill any pymobiledevice3 simulate-location processes left over from a
    previous crashed/force-quit session.  This prevents GPS jitter caused by
    two competing location injectors running simultaneously.
    """
    try:
        if sys.platform == "win32":
            # Use tasklist to find pymobiledevice3 processes on Windows
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5
            )
            # Also try wmic for command line inspection
            result2 = subprocess.run(
                ["wmic", "process", "where",
                 "commandline like '%simulate-location%play%'",
                 "get", "processid"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result2.returncode == 0:
                lines = result2.stdout.strip().split('\n')
                for line in lines[1:]:  # skip header
                    pid = line.strip()
                    if pid.isdigit():
                        try:
                            subprocess.run(
                                ["taskkill", "/F", "/PID", pid],
                                capture_output=True, timeout=5,
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                            print(f"[Startup Cleanup] Killed orphaned simulate-location process PID {pid}")
                        except Exception:
                            pass
        else:
            # macOS / Linux logic using pkill -f
            subprocess.run(
                ["pkill", "-f", "simulate-location.*play"],
                capture_output=True, timeout=5
            )
            print("[Startup Cleanup] Cleaned up orphaned location processes (macOS/Linux)")
    except Exception as e:
        # Not critical — just log and continue
        print(f"[Startup Cleanup] Could not scan for orphans: {e}")


def _clear_stale_simulation():
    """
    Attempt to send a simulate-location clear command via the tunneld.
    This restores the phone's real GPS if it was left in a spoofed state
    by a previous crash.  Runs silently — failure is fine (phone may not
    be plugged in yet).
    """
    import socket
    try:
        # Quick check if tunneld is even running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        if sock.connect_ex(('127.0.0.1', 49151)) != 0:
            sock.close()
            return  # tunneld not running, nothing to clear
        sock.close()

        # Query tunneld for connected devices
        import requests as _req
        resp = _req.get("http://127.0.0.1:49151/", timeout=3)
        tunnels = resp.json()
        if not tunnels:
            return

        # Pick the first tunnel
        for udid, info in tunnels.items():
            addr = info.get("tunnel-address") or info.get("address")
            port = info.get("tunnel-port") or info.get("port")
            if addr and port:
                cmd = [
                    "pymobiledevice3", "developer", "dvt",
                    "simulate-location", "clear",
                    "--rsd", str(addr), str(port)
                ]
                subprocess.run(
                    cmd, capture_output=True, timeout=8,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                print(f"[Startup Cleanup] Cleared stale GPS simulation on device {udid[:8]}...")
            break  # only first device
    except Exception:
        pass  # silent — phone might not be connected


def _emergency_cleanup(*args):
    """
    Last-resort cleanup invoked by atexit or OS signal.
    Kills any simulate-location play processes so the phone reverts to real GPS.
    """
    try:
        config = ConfigManager()
        is_frozen = config.get('features.is_frozen', False)
    except Exception:
        is_frozen = False

    try:
        if sys.platform == "win32":
            subprocess.run(
                ["wmic", "process", "where",
                 "commandline like '%simulate-location%play%'",
                 "call", "terminate"],
                capture_output=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            subprocess.run(
                ["pkill", "-f", "simulate-location.*play"],
                capture_output=True, timeout=5
            )
    except Exception:
        pass

    # Also try to clear the simulation on the device if not frozen
    if not is_frozen:
        try:
            _clear_stale_simulation()
        except Exception:
            pass


def main():
    """Application entry point"""
    
    # Initialize logger
    logger = setup_logger()
    logger.info("Starting Marcel Location Simulator...")

    # Load configuration first
    config = ConfigManager()
    is_frozen = config.get('features.is_frozen', False)

    # --- Phase 0: Clean up leftovers from any previous crash ---
    logger.info("Checking for orphaned processes from previous session...")
    _cleanup_orphan_processes()
    
    if not is_frozen:
        _clear_stale_simulation()
    else:
        logger.info("Device is marked as FROZEN. Skipping automatic startup GPS clear.")

    # Register safety nets so force-quit still cleans up the phone
    atexit.register(_emergency_cleanup)
    signal.signal(signal.SIGINT, _emergency_cleanup)
    signal.signal(signal.SIGTERM, _emergency_cleanup)
    
    try:
        logger.info(f"Config loaded: {config.get('app.name')} v{config.get('app.version')}")
        
        # Initialize Qt Application
        app = QApplication(sys.argv)
        app.setApplicationName("Marcel Location Simulator")
        app.setApplicationVersion(config.get('app.version'))
        app.setOrganizationName("Marcel Afsar")
        
        # Set default font
        font = QFont("Segoe UI", 10)
        app.setFont(font)
        
        # Create and show main window
        global _main_window
        _main_window = MainWindow()
        _main_window.show()
        
        logger.info("Application started successfully")
        
        # Start event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application startup error: {e}", exc_info=True)
        _emergency_cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()