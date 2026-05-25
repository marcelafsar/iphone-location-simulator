"""
Main Window - Marcel Location Simulator
Premium PyQt6 desktop app with WASD joystick, phone detection, and route simulation.
Created by Marcel Afsar
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from loguru import logger

from core.device_manager import DeviceManager
from core.location_controller import LocationController
from gui.control_panel import ControlPanel
from gui.map_widget import MapWidget
from utils.config_manager import ConfigManager


class WalkSimulationThread(QThread):
    """Runs route simulation in a background thread to keep UI responsive"""
    
    progress_updated = pyqtSignal(float, float, float)  # lat, lon, progress
    route_calculated = pyqtSignal(float, float)  # total_dist, total_time
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, location_controller, start_lat, start_lon, end_lat, end_lon, speed, interval, simulate_stops: bool, transport_mode: str = 'driving'):
        super().__init__()
        self.location_controller = location_controller
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.end_lat = end_lat
        self.end_lon = end_lon
        self.speed = speed
        self.interval = interval
        self.simulate_stops = simulate_stops
        self.transport_mode = transport_mode

    def run(self):
        try:
            success = self.location_controller.simulate_walk(
                self.start_lat,
                self.start_lon,
                self.end_lat,
                self.end_lon,
                self.speed,
                self.interval,
                self.progress_updated.emit,
                self.simulate_stops,
                self.transport_mode,
                self.route_calculated.emit
            )
            if success:
                self.finished.emit()
            else:
                self.error.emit("Route simulation was interrupted")
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.config = ConfigManager()
        self.device_manager = DeviceManager()
        self.location_controller = None
        self.walk_thread = None
        self.total_dist = 0.0
        self.total_time = 0.0
        
        self._init_ui()
        self._load_stylesheet()
        self._setup_status_check()
        
    def _init_ui(self):
        """Initialize the UI with fullscreen map and floating overlay panels"""
        self.setWindowTitle("Marcel Location Simulator")
        self.resize(1200, 850)
        self.setMinimumSize(1100, 700)
        
        # Central widget
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        # Map widget (full background)
        self.map_widget = MapWidget(self.central_widget)
        self.map_widget.setGeometry(0, 0, self.width(), self.height())
        
        # Floating device info bar (top left)
        self.device_bar = self._create_device_bar()
        self.device_bar.setParent(self.central_widget)
        self.device_bar.setGeometry(20, 20, 500, 60)
        
        # Floating control panel (left side) wrapped in a scroll area to prevent squishing
        self.scroll_area = QScrollArea(self.central_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollArea > QWidget > QWidget { background: transparent; }")
        
        self.control_panel = ControlPanel()
        self.scroll_area.setWidget(self.control_panel)
        self.scroll_area.setFixedWidth(500)
        self.scroll_area.move(20, 95)
        
        # Toggle Menu Button
        self.toggle_menu_btn = QPushButton("◀ Hide", self.central_widget)
        self.toggle_menu_btn.setObjectName("toggle_menu_btn")
        self.toggle_menu_btn.setGeometry(525, 95, 80, 36)
        self.toggle_menu_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(22, 24, 30, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 18px;
                color: #e8e8ed;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2a2b35; }
        """)
        self.toggle_menu_btn.clicked.connect(self._on_toggle_menu)
        
        # Floating Map Control Buttons (Bottom Right)
        self.focus_btn = QPushButton("🎯 Focus", self.central_widget)
        self.focus_btn.setObjectName("focus_btn")
        self.focus_btn.setToolTip("Focus map on current spoofed location")
        self.focus_btn.clicked.connect(self._on_focus_location)
        
        self.track_btn = QPushButton("🔒 Track", self.central_widget)
        self.track_btn.setObjectName("track_btn")
        self.track_btn.setToolTip("Auto-center map as location travels")
        self.track_btn.setCheckable(True)
        self.track_btn.setChecked(True)
        self.track_btn.clicked.connect(self._on_focus_location)
        
        # GPS HUD Card (Bottom Right)
        self.gps_hud_card = QWidget(self.central_widget)
        self.gps_hud_card.setObjectName("gps_hud_card")
        self.gps_hud_card.setVisible(False)
        
        hud_layout = QVBoxLayout(self.gps_hud_card)
        hud_layout.setContentsMargins(16, 12, 16, 12)
        hud_layout.setSpacing(2)
        
        self.hud_header = QLabel("🚗  ACTIVE GPS NAVIGATION")
        self.hud_header.setObjectName("gps_hud_header")
        hud_layout.addWidget(self.hud_header)
        
        self.hud_time = QLabel("-- min")
        self.hud_time.setObjectName("gps_hud_time")
        hud_layout.addWidget(self.hud_time)
        
        self.hud_details = QLabel("Arrival: --  •  0.0 km remaining")
        self.hud_details.setObjectName("gps_hud_details")
        hud_layout.addWidget(self.hud_details)
        
        # Connect signals
        self.control_panel.set_location_requested.connect(self._on_set_location)
        self.control_panel.set_destination_requested.connect(self._on_destination_set)
        self.control_panel.walk_simulation_requested.connect(self._on_walk_simulation)
        self.control_panel.stop_requested.connect(self._on_stop)
        self.control_panel.clear_requested.connect(self._on_clear)
        self.control_panel.joystick_step_requested.connect(self._on_joystick_step)
        self.map_widget.location_clicked.connect(self._on_map_clicked)
        self.map_widget.destination_clicked.connect(self._on_map_destination_clicked)
        
        # Enable keyboard focus for WASD
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        
        # Disable controls until connected
        self.control_panel.set_enabled(False)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready — Connect your iPhone to get started")
        
        logger.info("UI initialized (Marcel Location Simulator)")
        
    def _create_device_bar(self) -> QWidget:
        """Create the floating device connection bar with phone info"""
        bar = QWidget()
        bar.setObjectName("device_bar")
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        
        # Device icon + status
        self.device_status_label = QLabel("📱  No device connected")
        self.device_status_label.setObjectName("device_status_label")
        self.device_status_label.setStyleSheet(
            "font-weight: 600; font-size: 12px; color: #ff453a; border: none; background: transparent;"
        )
        layout.addWidget(self.device_status_label, 1)
        
        # Battery label (hidden until connected)
        self.battery_label = QLabel("")
        self.battery_label.setObjectName("battery_label")
        self.battery_label.setStyleSheet(
            "font-size: 11px; color: #b0b3c6; border: none; background: transparent;"
        )
        self.battery_label.hide()
        layout.addWidget(self.battery_label)
        
        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("connect_btn")
        self.connect_btn.clicked.connect(self._on_connect)
        self.connect_btn.setFixedWidth(100)
        layout.addWidget(self.connect_btn)
        
        return bar

    def _on_toggle_menu(self):
        """Toggle control panel and device bar visibility"""
        is_visible = self.scroll_area.isVisible()
        self.scroll_area.setVisible(not is_visible)
        self.device_bar.setVisible(not is_visible)
        
        if is_visible:
            self.toggle_menu_btn.setText("▶ Menu")
            self.toggle_menu_btn.move(20, 20)
        else:
            self.toggle_menu_btn.setText("◀ Hide")
            self.toggle_menu_btn.move(525, 95)

    def _load_stylesheet(self):
        """Load QSS stylesheet"""
        qss_path = Path(__file__).parent / "style.qss"
        if qss_path.exists():
            try:
                self.setStyleSheet(qss_path.read_text(encoding='utf-8'))
                logger.info("Stylesheet applied")
            except Exception as e:
                logger.error(f"Failed to load stylesheet: {e}")
    
    def _setup_status_check(self):
        """Setup timer for periodic device status checks"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_device_status)
        self.status_timer.start(3000)  # Check every 3 seconds
    
    def _check_device_status(self):
        """Check device connection status and update UI"""
        if self.device_manager.is_connected():
            device_info = self.device_manager.get_device_info()
            if device_info:
                name = device_info.get('name', 'iPhone')
                model = device_info.get('model', '')
                version = device_info.get('version', '')
                battery = device_info.get('battery_level')
                
                status = f"📱  {name}"
                if model and model != name:
                    status += f"  •  {model}"
                if version:
                    status += f"  •  {version}"
                    
                self.device_status_label.setText(status)
                self.device_status_label.setStyleSheet(
                    "font-weight: 600; font-size: 12px; color: #34c759; border: none; background: transparent;"
                )
                
                # Battery indicator
                if battery is not None:
                    bat_icon = "🔋" if battery > 20 else "🪫"
                    self.battery_label.setText(f"{bat_icon} {battery}%")
                    self.battery_label.setStyleSheet(
                        f"font-size: 11px; color: {'#34c759' if battery > 20 else '#ff453a'}; "
                        "font-weight: 600; border: none; background: transparent;"
                    )
                    self.battery_label.show()
                else:
                    self.battery_label.hide()
        else:
            self.device_status_label.setText("📱  No device connected")
            self.device_status_label.setStyleSheet(
                "font-weight: 600; font-size: 12px; color: #ff453a; border: none; background: transparent;"
            )
            self.battery_label.hide()
            self.connect_btn.setText("Connect")
            self.control_panel.set_enabled(False)
            
    def _on_connect(self):
        """Handle connect/disconnect button"""
        if self.device_manager.is_connected():
            # Disconnect
            if self.location_controller:
                self.location_controller.clear_location()
            self.device_manager.disconnect()
            self.location_controller = None
            self.connect_btn.setText("Connect")
            self.control_panel.set_enabled(False)
            self.battery_label.hide()
            self.statusBar.showMessage("Disconnected from device")
            logger.info("Disconnected from device")
        else:
            # Connect
            self.statusBar.showMessage("Connecting to iPhone...")
            self.connect_btn.setText("...")
            self.connect_btn.setEnabled(False)
            
            # Force UI update before blocking call
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            if self.device_manager.connect():
                self.location_controller = LocationController(self.device_manager)
                self.connect_btn.setText("Disconnect")
                self.connect_btn.setEnabled(True)
                self.control_panel.set_enabled(True)
                
                device_info = self.device_manager.get_device_info()
                name = device_info.get('name', 'iPhone') if device_info else 'iPhone'
                self.statusBar.showMessage(f"Connected to {name}")
                
                # Do NOT automatically drop a marker on the map so it stays blank
                # until the user specifically searches or clicks somewhere.
                self.statusBar.showMessage(f"Connected to {name}. Search for an address or click the map to set a location.")
                
                logger.info("Device connected successfully")
            else:
                self.connect_btn.setText("Connect")
                self.connect_btn.setEnabled(True)
                self.statusBar.showMessage("Connection failed")
                QMessageBox.warning(
                    self,
                    "Connection Error",
                    "Could not connect to your iPhone.\n\n"
                    "Please check:\n"
                    "1. iPhone is connected via USB\n"
                    "2. Developer Mode is enabled\n"
                    "   (Settings > Privacy & Security > Developer Mode)\n"
                    "3. Screen is unlocked and you tapped 'Trust'\n"
                    "4. This app is running as Administrator"
                )
                logger.error("Device connection failed")
    
    def _on_set_location(self, lat: float, lon: float):
        """Teleport to location"""
        if not self.location_controller:
            return
        
        if self.location_controller.set_location(lat, lon):
            self.map_widget.set_center(lat, lon)
            self.map_widget.add_marker(lat, lon)
            self.statusBar.showMessage(f"Teleported to ({lat:.6f}, {lon:.6f})")
            logger.info(f"Location set: ({lat}, {lon})")
        else:
            QMessageBox.critical(self, "Error", "Failed to set location. Check the RSD tunnel connection.")
            
    def _on_map_clicked(self, lat: float, lon: float):
        """Handle map click — update start coordinate inputs"""
        self.control_panel.set_coordinates(lat, lon)
        self.statusBar.showMessage(f"Selected Start: ({lat:.6f}, {lon:.6f})")
        
        if self.device_manager.is_connected():
            self._on_set_location(lat, lon)

    def _on_map_destination_clicked(self, lat: float, lon: float):
        """Handle map right-click or drag for Destination Location"""
        self.control_panel.set_end_location(lat, lon)
        self.map_widget.run_js(f"setDestination({lat}, {lon});")
        self.statusBar.showMessage(f"Selected Destination: ({lat:.6f}, {lon:.6f})")

    def _on_destination_set(self, lat: float, lon: float):
        """Update destination marker visually from control panel"""
        if self.device_manager.is_connected():
            self.map_widget.run_js(f"setDestination({lat}, {lon});")
            
    def _on_walk_simulation(self, start_lat, start_lon, end_lat, end_lon, speed, interval, simulate_stops, transport_mode='driving'):
        """Start route simulation"""
        if not self.location_controller:
            QMessageBox.warning(self, "Error", "No device connected")
            return

        self.total_dist = 0.0
        self.total_time = 0.0
        self.gps_hud_card.setVisible(False)

        # Set starting position on device and map
        self.location_controller.set_location(start_lat, start_lon)
        self.map_widget.add_marker(start_lat, start_lon)

        # Pre-fetch OSRM road route to show on map before movement begins
        try:
            route_data = self.location_controller._get_road_route(
                start_lat, start_lon, end_lat, end_lon, transport_mode
            )
            if route_data and route_data.get('geometry'):
                coords = route_data['geometry']['coordinates']
                road_waypoints = [(lat, lon) for lon, lat in coords]
                self.map_widget.show_route(road_waypoints, show_markers=True, auto_fit=True)
            else:
                # Straight-line fallback
                waypoints = [(start_lat, start_lon), (end_lat, end_lon)]
                self.map_widget.show_route(waypoints, show_markers=True, auto_fit=True)
        except Exception as e:
            logger.warning(f"Could not pre-fetch route for map preview: {e}")
            waypoints = [(start_lat, start_lon), (end_lat, end_lon)]
            self.map_widget.show_route(waypoints, show_markers=True, auto_fit=True)

        # Run simulation in background thread
        self.walk_thread = WalkSimulationThread(
            self.location_controller,
            start_lat, start_lon,
            end_lat, end_lon,
            speed, interval,
            simulate_stops,
            transport_mode
        )
        self.walk_thread.progress_updated.connect(self._on_walk_progress)
        self.walk_thread.route_calculated.connect(self._on_walk_route_calculated)
        self.walk_thread.finished.connect(self._on_walk_finished)
        self.walk_thread.error.connect(self._on_walk_error)
        self.walk_thread.start()

        mode_labels = {
            'walking': '🚶 Walking', 'cycling': '🚲 Cycling',
            'driving': '🚗 City Drive', 'highway': '🛣️ Highway'
        }
        label = mode_labels.get(transport_mode, transport_mode)
        self.statusBar.showMessage(f"Simulating route — {label} at {speed:.0f} km/h")
        logger.info(f"Route simulation started: {speed} km/h, mode={transport_mode}, traffic={simulate_stops}")
    
    def _on_walk_route_calculated(self, total_dist: float, total_time: float):
        """Called when total route distance and duration are calculated"""
        self.total_dist = total_dist
        self.total_time = total_time
        
        # Display HUD card
        self.gps_hud_card.setVisible(True)
        self._update_hud_display(0.0)

    def _update_hud_display(self, progress: float):
        """Calculate and render remaining distance, time, and ETA on the HUD"""
        if not self.gps_hud_card.isVisible():
            return
            
        if progress < 0:
            self.hud_time.setText("PAUSED")
            self.hud_details.setText("Waiting at traffic stop...")
            return

        rem_time = max(0.0, (1.0 - progress) * self.total_time)
        rem_dist = max(0.0, (1.0 - progress) * self.total_dist)
        rem_dist_km = rem_dist / 1000.0

        # Format remaining time
        if rem_time >= 3600:
            h = int(rem_time // 3600)
            m = int((rem_time % 3600) // 60)
            time_text = f"{h} hr {m} min"
        elif rem_time >= 60:
            m = int(rem_time // 60)
            time_text = f"{m} min"
        else:
            time_text = f"{int(rem_time)} sec"

        # Calculate dynamic ETA
        from datetime import datetime, timedelta
        eta = datetime.now() + timedelta(seconds=rem_time)
        eta_str = eta.strftime("%I:%M %p")

        self.hud_time.setText(time_text)
        self.hud_details.setText(f"Arrival: {eta_str}  •  {rem_dist_km:.1f} km remaining")

    def _on_walk_progress(self, lat: float, lon: float, progress: float):
        """Update UI with simulation progress"""
        self.map_widget.add_marker(lat, lon)
        self.control_panel.set_coordinates(lat, lon)
        
        # Live HUD calculation
        self._update_hud_display(progress)
        
        # Auto-center map if track toggle is active
        if self.track_btn.isChecked() and progress >= 0:
            self.map_widget.set_center(lat, lon)
        
        if progress < 0:
            self.statusBar.showMessage(f"⏸  Waiting at traffic stop... ({lat:.6f}, {lon:.6f})")
        else:
            self.statusBar.showMessage(f"▶  {progress*100:.0f}% — ({lat:.6f}, {lon:.6f})")
    
    def _on_walk_finished(self):
        """Route simulation completed"""
        self.statusBar.showMessage("✅  Route simulation complete")
        self.gps_hud_card.setVisible(False)
        QMessageBox.information(self, "Complete", "Route simulation has finished.")
    
    def _on_walk_error(self, error_msg: str):
        self.statusBar.showMessage(f"Error: {error_msg}")
        self.gps_hud_card.setVisible(False)
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_msg}")
        
    def _on_focus_location(self):
        """Pan map back to current spoofed location"""
        if not self.location_controller:
            return
        loc = self.location_controller.get_current_location()
        if loc:
            self.map_widget.set_center(loc[0], loc[1])
            self.statusBar.showMessage(f"Map focused on: ({loc[0]:.6f}, {loc[1]:.6f})")
            
    def _on_joystick_step(self, direction: str):
        """Handle D-Pad / WASD joystick step"""
        if not self.location_controller:
            return
            
        current_loc = self.location_controller.get_current_location()
        if not current_loc:
            current_loc = (self.control_panel.lat_input.value(), self.control_panel.lon_input.value())
            
        lat, lon = current_loc
        
        # Scale step size based on speed setting
        speed = self.control_panel.speed_slider.value() / 10.0
        step_factor = max(0.00003, (speed / 10.0) * 0.0001)
        
        if direction == "N":
            lat += step_factor
        elif direction == "S":
            lat -= step_factor
        elif direction == "E":
            lon += step_factor
        elif direction == "W":
            lon -= step_factor
            
        if self.location_controller.set_location(lat, lon):
            self.map_widget.add_marker(lat, lon)
            self.map_widget.set_center(lat, lon)
            self.control_panel.set_coordinates(lat, lon)
            self.statusBar.showMessage(f"Moved to ({lat:.6f}, {lon:.6f})")
            
    def _on_stop(self):
        """Stop simulation"""
        self.gps_hud_card.setVisible(False)
        if self.location_controller:
            self.location_controller.stop_simulation()
            if self.walk_thread and self.walk_thread.isRunning():
                self.walk_thread.terminate()
                self.walk_thread.wait()
            self.statusBar.showMessage("Simulation stopped")
    
    def _on_clear(self):
        """Reset GPS to real location"""
        self._on_stop()
        self.gps_hud_card.setVisible(False)
        if self.location_controller:
            self.statusBar.showMessage("Resetting GPS...")
            if self.location_controller.clear_location():
                self.map_widget.clear_markers()
                self.map_widget.clear_route_lines()
                self.statusBar.showMessage("GPS reset to real location. Map cleared.")
                
    def keyPressEvent(self, event):
        """Hook WASD and arrow keys for joystick control"""
        if not self.device_manager.is_connected() or not self.location_controller:
            super().keyPressEvent(event)
            return
            
        key = event.key()
        if key == Qt.Key.Key_W or key == Qt.Key.Key_Up:
            self._on_joystick_step("N")
        elif key == Qt.Key.Key_S or key == Qt.Key.Key_Down:
            self._on_joystick_step("S")
        elif key == Qt.Key.Key_D or key == Qt.Key.Key_Right:
            self._on_joystick_step("E")
        elif key == Qt.Key.Key_A or key == Qt.Key.Key_Left:
            self._on_joystick_step("W")
        else:
            super().keyPressEvent(event)
            
    def resizeEvent(self, event):
        """Resize map and reposition bottom right controls responsive to window sizes"""
        super().resizeEvent(event)
        self.map_widget.setGeometry(0, 0, self.width(), self.height())
        if hasattr(self, 'scroll_area'):
            self.scroll_area.setFixedHeight(self.height() - 115)

        hud_w = 320
        hud_h = 110
        btn_w = 90
        btn_h = 36
        margin = 20

        if hasattr(self, 'gps_hud_card'):
            self.gps_hud_card.setGeometry(
                self.width() - hud_w - margin,
                self.height() - hud_h - margin - 35,
                hud_w,
                hud_h
            )

        if hasattr(self, 'focus_btn') and hasattr(self, 'track_btn'):
            self.track_btn.setGeometry(
                self.width() - btn_w - margin,
                self.height() - hud_h - margin - 35 - btn_h - 10,
                btn_w,
                btn_h
            )
            self.focus_btn.setGeometry(
                self.width() - (btn_w * 2) - margin - 10,
                self.height() - hud_h - margin - 35 - btn_h - 10,
                btn_w,
                btn_h
            )
        
    def closeEvent(self, event):
        """Clean up on window close"""
        if self.device_manager.is_connected():
            if self.location_controller:
                self.location_controller.clear_location()
            self.device_manager.disconnect()
        event.accept()