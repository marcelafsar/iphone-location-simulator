"""
iPhone Device Connection Manager (Remote Tunneld / Windows / pymobiledevice3)
Created by Marcel Afsar
"""

from __future__ import annotations

import subprocess
import sys
import time
import socket
from typing import Optional, Dict, Any, List, Tuple
import requests
from loguru import logger


class DeviceManager:
    """Manages iPhone device connections via Remote Tunneld with auto-start support"""

    TUNNELD_URL = "http://127.0.0.1:49151"

    def __init__(self):
        self._device_info: Optional[dict] = None
        self._is_connected: bool = False
        self._rsd_address: Optional[str] = None
        self._rsd_port: Optional[int] = None

    # ----------------------------
    # Internal helpers
    # ----------------------------
    def _start_tunneld_process(self) -> bool:
        """Start pymobiledevice3 remote tunneld as a hidden background process on Windows"""
        # Check if port is already in use
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('127.0.0.1', 49151))
            sock.close()
            if result == 0:
                logger.info("Tunneld is already running (port 49151 in use)")
                return True
        except Exception:
            pass

        logger.info("Starting 'pymobiledevice3 remote tunneld' in background...")
        try:
            startupinfo = None
            creationflags = 0
            
            if sys.platform == "win32":
                # Hide the console window on Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW

            cmd = [sys.executable, "-m", "pymobiledevice3", "remote", "tunneld"]
            
            subprocess.Popen(
                cmd,
                startupinfo=startupinfo,
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for the daemon to start (max 5 seconds)
            for i in range(10):
                time.sleep(0.5)
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    result = sock.connect_ex(('127.0.0.1', 49151))
                    sock.close()
                    if result == 0:
                        logger.info(f"Tunneld daemon started successfully (attempt {i+1})")
                        return True
                except Exception:
                    pass
            
            logger.warning("Tunneld daemon start could not be verified. Timed out.")
            return False

        except Exception as e:
            logger.error(f"Failed to start tunneld daemon process: {e}")
            return False

    def _get_tunnels_raw(self) -> Dict[str, List[Dict[str, Any]]]:
        """Query tunneld GET / (List Tunnels) and return raw JSON."""
        url = f"{self.TUNNELD_URL}/"
        r = requests.get(url, timeout=3)
        r.raise_for_status()

        data = r.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected tunneld response type: {type(data)}")

        return data

    def _pick_first_tunnel(self, data: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, Dict[str, Any]]:
        """Pick the first UDID and tunnel from the raw tunnels dict."""
        if not data:
            raise RuntimeError("No active tunnels found. Make sure your iPhone is connected, Developer Mode is on, and you tapped 'Trust'.")

        udid, tunnels = next(iter(data.items()))
        if not tunnels or not isinstance(tunnels, list):
            raise RuntimeError(f"No tunnel info for {udid}")

        tunnel = tunnels[0]
        if not isinstance(tunnel, dict):
            raise RuntimeError(f"Unexpected tunnel item type: {type(tunnel)}")

        return udid, tunnel

    def _fetch_device_details(
        self,
        udid: str,
        rsd_address: Optional[str] = None,
        rsd_port: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch device details (name, model, iOS version, battery) via pymobiledevice3.
        Uses the RSD tunnel when available for the most accurate info.
        """
        info = {
            "name": "",
            "model": "Unknown Model",
            "version": "iOS",
            "udid": udid,
            "battery_level": None,
            "battery_charging": False,
        }

        rsd_args = ["--rsd", rsd_address, str(rsd_port)] if rsd_address and rsd_port else []

        # Primary: lockdown info via RSD tunnel (most reliable path)
        try:
            cmd = [sys.executable, "-m", "pymobiledevice3", "lockdown", "info"] + rsd_args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            if result.returncode == 0 and result.stdout.strip():
                self._parse_lockdown_output(result.stdout, info)
        except Exception as e:
            logger.debug(f"lockdown info failed: {e}")

        # Secondary: usbmux list (fills gaps if lockdown info didn't get everything)
        if not info["name"] or info["model"] == "Unknown Model":
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pymobiledevice3", "usbmux", "list", "--no-color"],
                    capture_output=True, text=True, timeout=8
                )
                if result.returncode == 0 and result.stdout.strip():
                    self._parse_lockdown_output(result.stdout, info)
            except Exception as e:
                logger.debug(f"usbmux list failed: {e}")

        # Final fallback: if name is still blank, use the model name
        if not info["name"]:
            info["name"] = info["model"] if info["model"] != "Unknown Model" else "iPhone"

        return info

    def _parse_lockdown_output(self, output: str, info: dict):
        """Parse pymobiledevice3 text/JSON output into device info dict in-place."""
        # Try JSON first (newer pymobiledevice3 versions output JSON)
        import json as _json
        try:
            data = _json.loads(output)
            if isinstance(data, dict):
                for key, val in data.items():
                    k = key.lower()
                    if k == "devicename" and not info["name"]:
                        info["name"] = self._clean_string(str(val))
                    elif k == "producttype" and info["model"] == "Unknown Model":
                        info["model"] = self._friendly_model_name(self._clean_string(str(val)))
                    elif k == "productversion":
                        info["version"] = "iOS " + self._clean_string(str(val))
                    elif k == "batterycurrentcapacity" and val is not None:
                        try:
                            info["battery_level"] = int(val)
                        except (ValueError, TypeError):
                            pass
                return  # JSON parsed successfully
        except (_json.JSONDecodeError, ValueError):
            pass

        # Fallback: line-by-line text parsing
        for line in output.splitlines():
            ll = line.lower().strip()
            if "devicename" in ll:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    candidate = self._clean_string(parts[1])
                    if candidate and not info["name"]:
                        info["name"] = candidate
            elif "producttype" in ll:
                parts = line.split(":", 1)
                if len(parts) > 1 and info["model"] == "Unknown Model":
                    info["model"] = self._friendly_model_name(self._clean_string(parts[1]))
            elif "productversion" in ll:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    info["version"] = "iOS " + self._clean_string(parts[1])
            elif "batterycurrentcapacity" in ll:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    try:
                        info["battery_level"] = int(parts[1].strip())
                    except ValueError:
                        pass

    @staticmethod
    def _clean_string(s: str) -> str:
        """Strip non-ASCII and control chars. Only keep printable ASCII (32-126)."""
        cleaned = ''.join(c for c in s if 32 <= ord(c) <= 126)
        return cleaned.strip().strip('"\'')

    @staticmethod
    def _friendly_model_name(raw: str) -> str:
        """Convert internal model identifiers to friendly names."""
        model_map = {
            "iPhone15,2": "iPhone 14 Pro",
            "iPhone15,3": "iPhone 14 Pro Max",
            "iPhone15,4": "iPhone 15",
            "iPhone15,5": "iPhone 15 Plus",
            "iPhone16,1": "iPhone 15 Pro",
            "iPhone16,2": "iPhone 15 Pro Max",
            "iPhone17,1": "iPhone 16 Pro",
            "iPhone17,2": "iPhone 16 Pro Max",
            "iPhone17,3": "iPhone 16",
            "iPhone17,4": "iPhone 16 Plus",
            "iPhone14,7": "iPhone 14",
            "iPhone14,8": "iPhone 14 Plus",
            "iPhone14,2": "iPhone 13 Pro",
            "iPhone14,3": "iPhone 13 Pro Max",
            "iPhone14,4": "iPhone 13 Mini",
            "iPhone14,5": "iPhone 13",
        }
        return model_map.get(raw, raw)

    def _build_device_info_minimal(self, udid: str, tunnel: Dict[str, Any]) -> Dict[str, Any]:
        """Build minimal device_info from tunneld data only."""
        return {
            "name": "iPhone",
            "model": "iPhone",
            "version": "iOS 17+",
            "udid": udid,
            "interface": tunnel.get("interface"),
            "battery_level": None,
            "battery_charging": False,
        }

    # ----------------------------
    # Public APIs
    # ----------------------------
    def connect(self) -> bool:
        """
        Connect to iPhone via Remote Tunneld (auto-starts daemon if needed).

        Returns:
            bool: True on success
        """
        try:
            logger.info("Starting iPhone connection sequence...")

            # 1. Auto-start tunnel daemon
            self._start_tunneld_process()

            # 2. Get tunnel info
            try:
                tunnels = self._get_tunnels_raw()
            except requests.RequestException as e:
                logger.error(f"Cannot connect to tunneld service: {e}")
                logger.error("Make sure pymobiledevice3 is installed and you're running as Administrator.")
                return False
            except Exception as e:
                logger.error(f"Failed to parse tunneld response: {e}")
                return False

            # 3. Extract connected device
            try:
                udid, tunnel = self._pick_first_tunnel(tunnels)
            except Exception as e:
                logger.error(str(e))
                return False

            # Get tunnel-address / tunnel-port
            rsd_addr = tunnel.get("tunnel-address")
            rsd_port = tunnel.get("tunnel-port")

            if not rsd_addr or not rsd_port:
                logger.error("Could not retrieve tunnel-address or tunnel-port")
                logger.error(f"tunnel={tunnel}")
                return False

            # 4. Fetch rich device details via RSD tunnel (most accurate)
            self._device_info = self._fetch_device_details(udid, str(rsd_addr), int(rsd_port))
            self._device_info["interface"] = tunnel.get("interface")
            self._rsd_address = str(rsd_addr)
            self._rsd_port = int(rsd_port)
            self._is_connected = True

            logger.info(f"Connected successfully: {self._device_info['name']} ({self._device_info['model']})")
            logger.info(f"UDID: {udid}")
            logger.info(f"RSD Tunnel: {self._rsd_address}:{self._rsd_port}")
            if self._device_info.get("battery_level") is not None:
                logger.info(f"Battery: {self._device_info['battery_level']}%")
            return True

        except Exception as e:
            logger.error(f"Unexpected error during device connection: {e}", exc_info=True)
            self._is_connected = False
            return False

    def disconnect(self):
        """Disconnect from iPhone"""
        logger.info("Disconnecting from iPhone...")
        self._is_connected = False
        self._device_info = None
        self._rsd_address = None
        self._rsd_port = None
        logger.info("Disconnected")

    def is_connected(self) -> bool:
        """Check connection status"""
        return self._is_connected

    def get_device_info(self) -> Optional[dict]:
        """Get device information"""
        return self._device_info

    def get_rsd_address(self) -> Optional[str]:
        """Get RSD address (= tunnel-address)"""
        return self._rsd_address

    def get_rsd_port(self) -> Optional[int]:
        """Get RSD port (= tunnel-port)"""
        return self._rsd_port

    def check_connection(self) -> bool:
        """
        Verify connection is still valid, reconnect if needed.

        Returns:
            bool: True if connection is active
        """
        if not self._is_connected:
            logger.warning("Connection lost. Attempting to reconnect...")
            return self.connect()

        try:
            tunnels = self._get_tunnels_raw()
            udid = (self._device_info or {}).get("udid")
            if not udid or udid not in tunnels:
                logger.warning("Previous device tunnel not found. Reconnecting...")
                self._is_connected = False
                return self.connect()

            tunnel_list = tunnels.get(udid) or []
            if not tunnel_list:
                logger.warning("Tunnel info is empty. Reconnecting...")
                self._is_connected = False
                return self.connect()

            tunnel = tunnel_list[0]
            rsd_addr = tunnel.get("tunnel-address")
            rsd_port = tunnel.get("tunnel-port")
            if not rsd_addr or not rsd_port:
                logger.warning("Tunnel info is incomplete. Reconnecting...")
                self._is_connected = False
                return self.connect()

            self._rsd_address = str(rsd_addr)
            self._rsd_port = int(rsd_port)
            return True

        except Exception as e:
            logger.warning(f"Connection check failed: {e}")
            self._is_connected = False
            return self.connect()

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def __del__(self):
        """Destructor"""
        if self._is_connected:
            self.disconnect()