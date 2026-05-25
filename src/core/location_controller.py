"""
Location Controller (GPX play method — flicker-free, road-snapping version)
Created by Marcel Afsar
"""

import subprocess
import threading
import tempfile
import time
import random
import requests
from pathlib import Path
from typing import Optional, Tuple, Callable, List, Dict
from loguru import logger

from core.device_manager import DeviceManager
from core.coordinate_utils import CoordinateUtils


class LocationController:
    """Controls iOS GPS location simulation via GPX play method"""

    # Speed caps per transport mode (km/h)
    SPEED_CAPS = {
        'walking': 8.0,
        'cycling': 30.0,
        'driving': 50.0,
        'highway': 90.0,
    }

    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager
        self._is_simulating: bool = False
        self._current_location: Optional[Tuple[float, float]] = None
        self._location_process: Optional[subprocess.Popen] = None
        self._process_lock = threading.Lock()

    # ----------------------------
    # Internal helpers
    # ----------------------------
    def _get_rsd_args(self) -> list:
        """Get RSD address and port as arguments for CLI tools"""
        rsd_address = self.device_manager.get_rsd_address()
        rsd_port = self.device_manager.get_rsd_port()
        if not rsd_address or not rsd_port:
            return []
        return ["--rsd", rsd_address, str(rsd_port)]

    def _stop_location_process(self):
        """Stop any actively running GPX play processes"""
        with self._process_lock:
            if self._location_process:
                try:
                    logger.debug("Terminating active location simulation process...")
                    self._location_process.terminate()
                    try:
                        self._location_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        logger.warning("Process did not respond. Force killing it...")
                        self._location_process.kill()
                        self._location_process.wait()
                    logger.debug("Location simulation process stopped successfully.")
                except Exception as e:
                    logger.error(f"Error terminating process: {e}")
                finally:
                    self._location_process = None

    def _terminate_process_safe(self, proc: subprocess.Popen):
        """Safely terminate a single process without holding the lock"""
        try:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        except Exception as e:
            logger.debug(f"Error terminating old process: {e}")

    def _create_gpx_file(self, latitude: float, longitude: float) -> str:
        """
        Generate a long-duration single-location GPX file.

        Uses two identical waypoints 24 hours apart so the GPX play process
        stays alive indefinitely — the iPhone holds the spoofed location
        without reverting to real GPS between joystick keystrokes.
        """
        from datetime import datetime, timedelta
        t1 = datetime.utcnow()
        t2 = t1 + timedelta(hours=24)
        gpx_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Marcel Location Simulator"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <trk>
    <name>Location</name>
    <trkseg>
      <trkpt lat="{latitude}" lon="{longitude}">
        <time>{t1.isoformat()}Z</time>
      </trkpt>
      <trkpt lat="{latitude}" lon="{longitude}">
        <time>{t2.isoformat()}Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False)
        temp_file.write(gpx_content)
        temp_file.close()
        return temp_file.name

    def _densify_waypoints(self, waypoints: List[Tuple[float, float, float]], max_gap_sec: float = 1.0) -> List[Tuple[float, float, float]]:
        """
        Interpolates waypoints to ensure no two consecutive points are separated by more than max_gap_sec.
        This prevents Apple Maps from dropping the GPS signal on long straight roads.
        """
        if not waypoints:
            return []
            
        densified = [waypoints[0]]
        for i in range(1, len(waypoints)):
            prev = waypoints[i - 1]
            curr = waypoints[i]
            
            time_gap = curr[2] - prev[2]
            if time_gap > max_gap_sec:
                # Need to insert intermediate points
                num_inserts = int(time_gap // max_gap_sec)
                for j in range(1, num_inserts + 1):
                    fraction = j / (num_inserts + 1)
                    interp_lat = prev[0] + (curr[0] - prev[0]) * fraction
                    interp_lon = prev[1] + (curr[1] - prev[1]) * fraction
                    interp_time = prev[2] + time_gap * fraction
                    densified.append((interp_lat, interp_lon, interp_time))
                    
            densified.append(curr)
            
        return densified

    def _create_route_gpx_file(self, waypoints: list) -> str:
        """
        Generate a multi-point route GPX file.
        Args:
            waypoints: List of (lat, lon, time_offset_seconds)
        """
        from datetime import datetime, timedelta
        gpx_content = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Marcel Location Simulator"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <trk>
    <name>Route</name>
    <trkseg>
"""
        start_time = datetime.utcnow()
        for lat, lon, time_offset in waypoints:
            point_time = start_time + timedelta(seconds=time_offset)
            gpx_content += f"""      <trkpt lat="{lat}" lon="{lon}">
        <time>{point_time.isoformat()}Z</time>
      </trkpt>
"""
        gpx_content += """    </trkseg>
  </trk>
</gpx>"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False)
        temp_file.write(gpx_content)
        temp_file.close()
        return temp_file.name

    def _get_road_route(
        self,
        start_lat: float, start_lon: float,
        end_lat: float, end_lon: float,
        mode: str = 'driving',
        include_steps: bool = True
    ) -> Optional[Dict]:
        """
        Fetch a road-following route from the public OSRM API.
        Returns the raw route dictionary (with geometry and steps) or None.
        """
        profile = 'driving' if mode not in ('walking', 'cycling') else mode

        url = (
            f"http://router.project-osrm.org/route/v1/{profile}/"
            f"{start_lon},{start_lat};{end_lon},{end_lat}"
            f"?overview=full&geometries=geojson&steps={'true' if include_steps else 'false'}"
        )
        try:
            r = requests.get(url, timeout=8)
            r.raise_for_status()
            data = r.json()
            if data.get('code') == 'Ok' and data.get('routes'):
                logger.info("OSRM route fetched successfully.")
                return data['routes'][0]
            else:
                logger.warning(f"OSRM returned no route: {data.get('code')}")
                return None
        except Exception as e:
            logger.warning(f"OSRM routing failed ({e}). Falling back to straight-line path.")
            return None

    # ----------------------------
    # Public APIs
    # ----------------------------
    def set_location(self, latitude: float, longitude: float) -> bool:
        """
        Spoof coordinates to a single specific location.
        Starts the new GPX process BEFORE killing the old one to eliminate
        the GPS snap-back gap that previously caused the location to jump.
        """
        if not self.device_manager.is_connected():
            logger.error("Device is not connected")
            return False

        try:
            rsd_args = self._get_rsd_args()
            if not rsd_args:
                logger.error("Could not obtain RSD connection arguments")
                return False

            gpx_file = self._create_gpx_file(latitude, longitude)
            logger.debug(f"GPX file created: {gpx_file}")

            cmd = [
                "pymobiledevice3", "developer", "dvt",
                "simulate-location", "play"
            ] + rsd_args + [gpx_file]

            logger.debug(f"Executing command: {' '.join(cmd)}")

            # Start NEW process FIRST — eliminates the GPS snap-back gap
            new_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Give new process ~150 ms to establish before swapping
            time.sleep(0.15)

            # Atomically swap: register new, grab reference to old
            with self._process_lock:
                old_process = self._location_process
                self._location_process = new_process

            # Terminate old process after new one is active
            if old_process:
                self._terminate_process_safe(old_process)

            # Verify new process is still alive
            if self._location_process and self._location_process.poll() is None:
                self._current_location = (latitude, longitude)
                self._is_simulating = True
                logger.info(f"Location spoofed (GPX play): ({latitude}, {longitude})")
                return True
            else:
                logger.error("Location spoofing process exited prematurely")
                try:
                    Path(gpx_file).unlink()
                except Exception:
                    pass
                return False

        except Exception as e:
            logger.error(f"Failed to spoof location: {e}", exc_info=True)
            return False

    def clear_location(self) -> bool:
        """Stop simulating location and restore real GPS coordinates"""
        if not self.device_manager.is_connected():
            logger.error("Device is not connected")
            return False

        self._stop_location_process()

        try:
            rsd_args = self._get_rsd_args()
            if not rsd_args:
                logger.error("Could not obtain RSD connection arguments")
                return False

            cmd = [
                "pymobiledevice3", "developer", "dvt",
                "simulate-location", "clear"
            ] + rsd_args

            logger.debug(f"Executing command: {' '.join(cmd)}")
            subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            self._is_simulating = False
            self._current_location = None
            logger.info("GPS location simulation cleared successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to clear GPS simulation: {e}", exc_info=True)
            self._is_simulating = False
            self._current_location = None
            return True

    def simulate_walk(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        speed_kmh: float = 5.0,
        update_interval: float = 1.0,
        progress_callback: Optional[Callable[[float, float, float], None]] = None,
        simulate_stops: bool = False,
        transport_mode: str = 'driving',
        route_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        Simulate realistic movement along roads between two coordinates.

        Uses OSRM to snap the path to real roads. Falls back to straight-line
        if OSRM is unreachable. Speed is capped per transport mode.
        """
        if not self.device_manager.is_connected():
            logger.error("Device is not connected")
            return False

        self._stop_location_process()

        try:
            # Enforce speed cap for the selected transport mode
            cap = self.SPEED_CAPS.get(transport_mode, 90.0)
            if speed_kmh > cap:
                logger.info(f"Speed {speed_kmh} km/h exceeds cap for '{transport_mode}' ({cap} km/h). Clamping.")
                speed_kmh = cap

            speed_ms = (speed_kmh * 1000) / 3600  # km/h → m/s

            # Try road-following route first
            route_data = self._get_road_route(
                start_lat, start_lon, end_lat, end_lon, transport_mode
            )

            timed_waypoints: List[Tuple[float, float, float]] = []
            elapsed = 0.0

            if route_data and route_data.get('geometry'):
                total_dist = route_data.get('distance', 0.0)
                coords = route_data['geometry']['coordinates']
                road_waypoints = [(lat, lon) for lon, lat in coords]
                
                # Identify stop coordinates from step maneuvers
                stop_coords = []  # list of (lat, lon)
                if simulate_stops and 'legs' in route_data:
                    for leg in route_data['legs']:
                        for step in leg.get('steps', []):
                            maneuver = step.get('maneuver', {})
                            m_type = maneuver.get('type')
                            # Pause at turns, exits, roundabouts, end of road
                            if m_type in ('turn', 'roundabout', 'exit roundabout', 'merge',
                                          'end of road', 'arrive', 'fork', 'new name'):
                                m_loc = maneuver.get('location')
                                if m_loc:
                                    stop_coords.append((m_loc[1], m_loc[0]))

                # Build timed waypoints
                for i, (lat, lon) in enumerate(road_waypoints):
                    if i == 0:
                        timed_waypoints.append((lat, lon, 0.0))
                    else:
                        prev_lat, prev_lon = road_waypoints[i - 1]
                        seg_dist = CoordinateUtils.calculate_distance(prev_lat, prev_lon, lat, lon)
                        elapsed += seg_dist / speed_ms
                        timed_waypoints.append((lat, lon, elapsed))

                        # Check if this waypoint is near any stop coordinate (within 30m)
                        if simulate_stops:
                            for sc in stop_coords:
                                d = CoordinateUtils.calculate_distance(lat, lon, sc[0], sc[1])
                                if d < 30:
                                    # Add a realistic 2-5s delay at this maneuver point
                                    import random as _rnd
                                    delay = _rnd.uniform(2.0, 5.0)
                                    elapsed += delay
                                    timed_waypoints.append((lat, lon, elapsed))
                                    stop_coords.remove(sc)
                                    break

                logger.info(f"Using OSRM route: {len(road_waypoints)} points, "
                            f"{len(stop_coords)} remaining unmatched stops")

            else:
                # Straight-line fallback: interpolate between start and end
                total_dist = CoordinateUtils.calculate_distance(start_lat, start_lon, end_lat, end_lon)
                steps = max(2, int(total_dist / max(1, speed_ms * update_interval)))
                route_points = [
                    (
                        start_lat + (end_lat - start_lat) * (i / steps),
                        start_lon + (end_lon - start_lon) * (i / steps)
                    )
                    for i in range(steps + 1)
                ]
                
                for i, (lat, lon) in enumerate(route_points):
                    if i == 0:
                        timed_waypoints.append((lat, lon, 0.0))
                    else:
                        prev_lat, prev_lon = route_points[i - 1]
                        seg_dist = CoordinateUtils.calculate_distance(prev_lat, prev_lon, lat, lon)
                        elapsed += seg_dist / speed_ms
                        timed_waypoints.append((lat, lon, elapsed))
                        
                logger.info(f"Using straight-line fallback: {len(route_points)} points")

            total_time = elapsed if elapsed > 0 else 1.0

            if route_callback:
                route_callback(total_dist, total_time)

            logger.info(
                f"Route simulation: {len(timed_waypoints)} waypoints, "
                f"speed={speed_kmh} km/h, mode={transport_mode}, "
                f"est. duration={total_time:.0f}s, traffic={simulate_stops}"
            )

            # Densify waypoints so GPX points are at most 1 second apart to prevent iOS GPS drop
            densified_waypoints = self._densify_waypoints(timed_waypoints, max_gap_sec=1.0)

            # Build and launch GPX
            gpx_file = self._create_route_gpx_file(densified_waypoints)
            rsd_args = self._get_rsd_args()
            if not rsd_args:
                logger.error("Could not obtain RSD connection arguments")
                return False

            cmd = [
                "pymobiledevice3", "developer", "dvt",
                "simulate-location", "play"
            ] + rsd_args + [gpx_file]

            logger.debug(f"Executing command: {' '.join(cmd)}")

            with self._process_lock:
                self._location_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            time.sleep(0.5)

            if not self._location_process or self._location_process.poll() is not None:
                logger.error("Failed to start route playback process")
                try:
                    Path(gpx_file).unlink()
                except Exception:
                    pass
                return False

            self._is_simulating = True

            # Progress tracking loop — update UI once per second, check cancel every 0.5s
            movement_elapsed = 0.0
            last_check_time = time.time()
            last_ui_update = 0.0

            while True:
                now = time.time()
                delta = now - last_check_time
                last_check_time = now

                if not self._is_simulating:
                    logger.info("Route simulation interrupted")
                    self._stop_location_process()
                    return False

                # Check if the GPX player process crashed
                with self._process_lock:
                    if self._location_process is None or self._location_process.poll() is not None:
                        logger.warning("GPX player process ended unexpectedly, restarting...")
                        # Rebuild and relaunch from current position
                        remaining = [(lat, lon, t - movement_elapsed)
                                     for lat, lon, t in densified_waypoints
                                     if t >= movement_elapsed]
                        if len(remaining) < 2:
                            break
                        # Re-zero timestamps
                        base = remaining[0][2]
                        remaining = [(lat, lon, t - base) for lat, lon, t in remaining]
                        restart_gpx = self._create_route_gpx_file(remaining)
                        self._location_process = subprocess.Popen(
                            cmd[:cmd.index(gpx_file)] + [restart_gpx],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        gpx_file = restart_gpx
                        time.sleep(0.3)

                movement_elapsed += delta
                if movement_elapsed >= total_time:
                    break

                progress = movement_elapsed / total_time

                # Interpolate current position from road waypoints (once per second)
                if movement_elapsed - last_ui_update >= 1.0:
                    last_ui_update = movement_elapsed
                    target_elapsed = progress * total_time
                    current_lat, current_lon = timed_waypoints[-1][0], timed_waypoints[-1][1]
                    for j in range(len(timed_waypoints) - 1):
                        t0 = timed_waypoints[j][2]
                        t1 = timed_waypoints[j + 1][2]
                        if t0 <= target_elapsed <= t1 and t1 > t0:
                            seg_p = (target_elapsed - t0) / (t1 - t0)
                            current_lat = timed_waypoints[j][0] + (timed_waypoints[j + 1][0] - timed_waypoints[j][0]) * seg_p
                            current_lon = timed_waypoints[j][1] + (timed_waypoints[j + 1][1] - timed_waypoints[j][1]) * seg_p
                            break

                    self._current_location = (current_lat, current_lon)

                    if progress_callback:
                        progress_callback(current_lat, current_lon, progress)

                time.sleep(0.5)

            self._current_location = (end_lat, end_lon)
            logger.info("Route simulation finished successfully")
            return True

        except Exception as e:
            logger.error(f"Error during route simulation: {e}", exc_info=True)
            self._is_simulating = False
            self._stop_location_process()
            return False

    def is_simulating(self) -> bool:
        """Check if active location simulation is running"""
        return self._is_simulating

    def get_current_location(self) -> Optional[Tuple[float, float]]:
        """Get the current simulated coordinates"""
        return self._current_location

    def stop_simulation(self):
        """Stop simulation playback"""
        self._is_simulating = False
        self._stop_location_process()
        logger.info("Simulation halted")

    def __del__(self):
        """Clean up by terminating the spoofing process"""
        self._stop_location_process()