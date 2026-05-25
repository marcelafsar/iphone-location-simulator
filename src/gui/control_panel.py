"""
Control Panel - Marcel Location Simulator
Premium floating sidebar with search, coordinates, route simulation, and joystick.
Created by Marcel Afsar
"""

import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QSlider, QDoubleSpinBox,
    QComboBox, QGridLayout, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger
from core.coordinate_utils import CoordinateUtils


class ControlPanel(QWidget):
    """Floating control panel widget"""
    
    # Signals
    set_location_requested = pyqtSignal(float, float)
    set_destination_requested = pyqtSignal(float, float)
    walk_simulation_requested = pyqtSignal(float, float, float, float, float, float, bool, str)
    stop_requested = pyqtSignal()
    clear_requested = pyqtSignal()
    freeze_requested = pyqtSignal()
    joystick_step_requested = pyqtSignal(str)  # 'N', 'S', 'E', 'W'
    roam_requested = pyqtSignal(float, float, float, float, float, str)
    roam_radius_changed = pyqtSignal(float, float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the control panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 1. Route Simulation (Main functionality)
        walk_group = self._create_walk_simulation_group()
        layout.addWidget(walk_group)
        
        # 2. Advanced Coordinates
        coord_group = self._create_coordinate_group()
        layout.addWidget(coord_group)
        
        # 3. Area Roaming
        roam_group = self._create_roam_group()
        layout.addWidget(roam_group)
        
        # 4. Joystick
        joystick_group = self._create_joystick_group()
        layout.addWidget(joystick_group)
        
        # 5. Controls
        control_group = self._create_control_buttons_group()
        layout.addWidget(control_group)
        
        layout.addStretch()
    
    def _create_walk_simulation_group(self) -> QGroupBox:
        """Route simulation settings with Address Inputs"""
        group = QGroupBox("🚗  Route Simulation")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 18, 10, 10)
        layout.setSpacing(8)
        
        # Start Address
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Start Address (e.g. Times Square)")
        self.search_input.returnPressed.connect(lambda: self._on_search(is_dest=False))
        
        start_layout = QHBoxLayout()
        start_layout.addWidget(self.search_input)
        self.search_btn = QPushButton("Set Start")
        self.search_btn.setFixedWidth(70)
        self.search_btn.clicked.connect(lambda: self._on_search(is_dest=False))
        start_layout.addWidget(self.search_btn)
        layout.addLayout(start_layout)
        
        # Dest Address
        self.dest_search_input = QLineEdit()
        self.dest_search_input.setPlaceholderText("Destination Address...")
        self.dest_search_input.returnPressed.connect(lambda: self._on_search(is_dest=True))
        
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(self.dest_search_input)
        self.dest_search_btn = QPushButton("Set Dest")
        self.dest_search_btn.setFixedWidth(70)
        self.dest_search_btn.clicked.connect(lambda: self._on_search(is_dest=True))
        dest_layout.addWidget(self.dest_search_btn)
        layout.addLayout(dest_layout)
        
        # Transport mode selector
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Mode:")
        mode_label.setFixedWidth(40)
        mode_layout.addWidget(mode_label)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "🤖 Auto (by distance)",
            "🚶 Walking  (≤8 km/h)",
            "🚲 Cycling  (≤30 km/h)",
            "🚗 City Drive  (≤50 km/h)",
            "🛣️ Highway  (≤90 km/h)"
        ])
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.preset_combo)
        layout.addLayout(mode_layout)

        # Speed slider
        speed_layout = QVBoxLayout()
        speed_label_layout = QHBoxLayout()
        speed_label_layout.addWidget(QLabel("Speed Override:"))
        self.speed_value_label = QLabel("5.0 km/h")
        self.speed_value_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        speed_label_layout.addWidget(self.speed_value_label)
        speed_label_layout.addStretch()
        speed_layout.addLayout(speed_label_layout)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(10, 500)
        self.speed_slider.setValue(350)
        self.speed_slider.valueChanged.connect(self._update_speed_label)
        speed_layout.addWidget(self.speed_slider)
        layout.addLayout(speed_layout)
        
        # Update interval
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Update Rate:")
        interval_label.setFixedWidth(70)
        interval_layout.addWidget(interval_label)
        self.interval_input = QDoubleSpinBox()
        self.interval_input.setRange(0.1, 10.0)
        self.interval_input.setValue(1.0)
        self.interval_input.setSingleStep(0.1)
        self.interval_input.setSuffix(" s")
        interval_layout.addWidget(self.interval_input)
        layout.addLayout(interval_layout)
        
        # Traffic stops checkbox
        self.stops_checkbox = QCheckBox("Simulate traffic lights, turns, exits")
        self.stops_checkbox.setStyleSheet("margin: 4px 0px; font-weight: 500; color: #34c759;")
        self.stops_checkbox.setChecked(True)
        layout.addWidget(self.stops_checkbox)
        
        # Start button
        self.walk_btn = QPushButton("▶  Calculate & Start Route")
        self.walk_btn.setObjectName("walk_btn")
        self.walk_btn.clicked.connect(self._on_walk_simulation)
        layout.addWidget(self.walk_btn)
        
        group.setLayout(layout)
        return group

    def _create_roam_group(self) -> QGroupBox:
        """Area Roaming Controls"""
        group = QGroupBox("🏞️  Area Roaming")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 18, 10, 10)
        layout.setSpacing(8)

        # Radius slider
        rad_layout = QHBoxLayout()
        rad_layout.addWidget(QLabel("Radius:"))
        self.radius_label = QLabel("500 m")
        self.radius_label.setStyleSheet("color: #34c759; font-weight: bold;")
        rad_layout.addWidget(self.radius_label)
        rad_layout.addStretch()
        layout.addLayout(rad_layout)

        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(50, 5000)
        self.radius_slider.setValue(500)
        self.radius_slider.valueChanged.connect(self._on_radius_changed)
        layout.addWidget(self.radius_slider)

        # Duration
        dur_layout = QHBoxLayout()
        dur_layout.addWidget(QLabel("Duration:"))
        self.duration_input = QDoubleSpinBox()
        self.duration_input.setRange(1.0, 1440.0)
        self.duration_input.setValue(30.0)
        self.duration_input.setSuffix(" min")
        dur_layout.addWidget(self.duration_input)
        layout.addLayout(dur_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.start_roam_btn = QPushButton("🚶 Start Roaming")
        self.start_roam_btn.clicked.connect(self._on_start_roaming)
        btn_layout.addWidget(self.start_roam_btn)

        self.stop_roam_btn = QPushButton("🔓 Stop Roaming")
        self.stop_roam_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(self.stop_roam_btn)

        layout.addLayout(btn_layout)

        # Info
        info = QLabel("Unplug safe: Phone will keep roaming within radius autonomously.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(info)

        group.setLayout(layout)
        return group

    def _create_coordinate_group(self) -> QGroupBox:
        """Advanced Coordinate Controls"""
        group = QGroupBox("📍  Advanced Coordinates")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 18, 10, 10)
        layout.setSpacing(6)
        
        grid = QGridLayout()
        
        # Start
        grid.addWidget(QLabel("Start Lat:"), 0, 0)
        self.lat_input = QDoubleSpinBox()
        self.lat_input.setRange(-90, 90)
        self.lat_input.setDecimals(6)
        self.lat_input.setValue(40.7128)
        grid.addWidget(self.lat_input, 0, 1)
        
        grid.addWidget(QLabel("Start Lon:"), 0, 2)
        self.lon_input = QDoubleSpinBox()
        self.lon_input.setRange(-180, 180)
        self.lon_input.setDecimals(6)
        self.lon_input.setValue(-74.0060)
        grid.addWidget(self.lon_input, 0, 3)

        # Dest
        grid.addWidget(QLabel("Dest Lat:"), 1, 0)
        self.end_lat_input = QDoubleSpinBox()
        self.end_lat_input.setRange(-90, 90)
        self.end_lat_input.setDecimals(6)
        self.end_lat_input.setValue(40.7580)
        grid.addWidget(self.end_lat_input, 1, 1)
        
        grid.addWidget(QLabel("Dest Lon:"), 1, 2)
        self.end_lon_input = QDoubleSpinBox()
        self.end_lon_input.setRange(-180, 180)
        self.end_lon_input.setDecimals(6)
        self.end_lon_input.setValue(-73.9855)
        grid.addWidget(self.end_lon_input, 1, 3)
        
        layout.addLayout(grid)
        
        btn_layout = QHBoxLayout()
        self.set_location_btn = QPushButton("⚡ Teleport to Start")
        self.set_location_btn.clicked.connect(self._on_set_location)
        btn_layout.addWidget(self.set_location_btn)
        
        self.copy_loc_btn = QPushButton("📋 Copy Start")
        self.copy_loc_btn.clicked.connect(self._on_copy_location)
        btn_layout.addWidget(self.copy_loc_btn)
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group
        
    def _on_copy_location(self):
        from PyQt6.QtWidgets import QApplication
        lat = self.lat_input.value()
        lon = self.lon_input.value()
        clipboard = QApplication.clipboard()
        clipboard.setText(f"{lat:.6f}, {lon:.6f}")
        logger.info(f"Copied to clipboard: {lat:.6f}, {lon:.6f}")

    def _create_joystick_group(self) -> QGroupBox:
        """D-Pad joystick for fine movement"""
        group = QGroupBox("🕹️  Joystick")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 22, 10, 10)
        
        desc = QLabel("Use buttons or WASD / Arrow keys to move step by step.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #b0b3c6; font-size: 11px;")
        layout.addWidget(desc)
        
        # D-PAD grid
        dpad_widget = QWidget()
        dpad_layout = QGridLayout(dpad_widget)
        dpad_layout.setContentsMargins(0, 5, 0, 0)
        dpad_layout.setSpacing(4)
        
        btn_style = "background-color: #2a2b35; border-radius: 6px; font-size: 16px; font-weight: bold;"
        
        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedSize(48, 40)
        self.btn_up.setStyleSheet(btn_style)
        self.btn_up.clicked.connect(lambda: self.joystick_step_requested.emit("N"))
        
        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedSize(48, 40)
        self.btn_down.setStyleSheet(btn_style)
        self.btn_down.clicked.connect(lambda: self.joystick_step_requested.emit("S"))
        
        self.btn_left = QPushButton("◀")
        self.btn_left.setFixedSize(48, 40)
        self.btn_left.setStyleSheet(btn_style)
        self.btn_left.clicked.connect(lambda: self.joystick_step_requested.emit("W"))
        
        self.btn_right = QPushButton("▶")
        self.btn_right.setFixedSize(48, 40)
        self.btn_right.setStyleSheet(btn_style)
        self.btn_right.clicked.connect(lambda: self.joystick_step_requested.emit("E"))
        
        dpad_layout.addWidget(self.btn_up, 0, 1, Qt.AlignmentFlag.AlignCenter)
        dpad_layout.addWidget(self.btn_left, 1, 0, Qt.AlignmentFlag.AlignCenter)
        dpad_layout.addWidget(self.btn_right, 1, 2, Qt.AlignmentFlag.AlignCenter)
        dpad_layout.addWidget(self.btn_down, 2, 1, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(dpad_widget, 0, Qt.AlignmentFlag.AlignCenter)
        group.setLayout(layout)
        return group
    
    def _create_control_buttons_group(self) -> QGroupBox:
        """Stop and reset controls"""
        group = QGroupBox("⚙️  Controls")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 18, 10, 10)
        layout.setSpacing(8)
        
        # Row 1: Stop and Reset GPS
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self.stop_btn = QPushButton("⏹  Stop")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.clicked.connect(self._on_stop)
        row1.addWidget(self.stop_btn)
        
        self.clear_btn = QPushButton("↩  Reset GPS")
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.clicked.connect(self._on_clear)
        row1.addWidget(self.clear_btn)
        layout.addLayout(row1)
        
        # Row 2: Freeze Location Button
        self.freeze_btn = QPushButton("❄️ Freeze Location")
        self.freeze_btn.setObjectName("freeze_btn")
        self.freeze_btn.clicked.connect(self._on_freeze)
        layout.addWidget(self.freeze_btn)
        
        # Row 3: Info note
        info_layout = QHBoxLayout()
        info_layout.setSpacing(6)
        
        self.info_icon = QLabel("ⓘ")
        self.info_icon.setStyleSheet("color: #6366F1; font-size: 14px; font-weight: bold; min-width: 12px;")
        info_layout.addWidget(self.info_icon)
        
        self.info_note = QLabel("Location will stay in the same exact spot and won't move until unfrozen or phone restarted")
        self.info_note.setWordWrap(True)
        self.info_note.setStyleSheet("color: #94A3B8; font-size: 11px; line-height: 14px;")
        info_layout.addWidget(self.info_note)
        
        layout.addLayout(info_layout)
        
        group.setLayout(layout)
        return group
    
    def _on_search(self, is_dest=False):
        """Search address via Nominatim OpenStreetMap"""
        input_box = self.dest_search_input if is_dest else self.search_input
        btn = self.dest_search_btn if is_dest else self.search_btn
        query = input_box.text().strip()
        if not query:
            return

        original_text = btn.text()
        btn.setText("...")
        btn.setEnabled(False)

        try:
            headers = {"User-Agent": "MarcelLocationSimulator/1.0"}
            url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=1"
            r = requests.get(url, headers=headers, timeout=6)
            r.raise_for_status()

            data = r.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                display_name = data[0].get("display_name", query)

                logger.info(f"Search result: {display_name} ({lat}, {lon})")
                if is_dest:
                    self.set_end_location(lat, lon)
                    self.set_destination_requested.emit(lat, lon)
                else:
                    self.set_coordinates(lat, lon)
                    self.set_location_requested.emit(lat, lon)
            else:
                QMessageBox.warning(self, "Not Found", f"Could not find: {query}")
        except Exception as e:
            logger.error(f"Search API error: {e}")
            QMessageBox.warning(self, "Search Error", str(e))
        finally:
            btn.setText(original_text)
            btn.setEnabled(True)
            
    def _on_mode_changed(self, index: int):
        """Update speed slider range and default value for the selected transport mode"""
        if index == 0:
            # Auto Mode - we don't change slider, just return
            return
            
        # config index is mapped to combo box index - 1
        config = [
            (80,   50),    # Walking:     max 8 km/h,  default 5 km/h
            (300,  150),   # Cycling:     max 30 km/h, default 15 km/h
            (500,  350),   # City Drive:  max 50 km/h, default 35 km/h
            (900,  800),   # Highway:     max 90 km/h, default 80 km/h
        ]
        cfg_idx = index - 1
        if 0 <= cfg_idx < len(config):
            max_val, default_val = config[cfg_idx]
            self.speed_slider.blockSignals(True)
            self.speed_slider.setRange(10, max_val)
            self.speed_slider.setValue(default_val)
            self.speed_slider.blockSignals(False)
            self._update_speed_label(default_val)

    def _get_transport_mode(self) -> str:
        """Return OSRM mode key for the currently selected transport combo item"""
        modes = ['walking', 'cycling', 'driving', 'highway']
        idx = self.preset_combo.currentIndex() - 1
        return modes[idx] if 0 <= idx < len(modes) else 'driving'
            
    def _update_speed_label(self, value: int):
        """Update speed display when slider changes"""
        speed = value / 10.0
        self.speed_value_label.setText(f"{speed:.1f} km/h")
        if self.preset_combo.currentIndex() != 0:
            current_preset = self.preset_combo.currentText()
            if ("Walking" in current_preset and value != 50) or \
               ("Cycling" in current_preset and value != 150) or \
               ("Driving" in current_preset and value != 600):
                self.preset_combo.setCurrentIndex(0)
    
    def _on_set_location(self):
        """Emit teleport request"""
        lat = self.lat_input.value()
        lon = self.lon_input.value()
        self.set_location_requested.emit(lat, lon)
    
    def _on_walk_simulation(self):
        """Emit route simulation request with transport mode"""
        start_lat = self.lat_input.value()
        start_lon = self.lon_input.value()
        end_lat = self.end_lat_input.value()
        end_lon = self.end_lon_input.value()
        
        mode_idx = self.preset_combo.currentIndex()
        if mode_idx == 0:  # Auto Mode
            dist_m = CoordinateUtils.calculate_distance(start_lat, start_lon, end_lat, end_lon)
            if dist_m < 2500:  # Less than 2.5km -> walk
                transport_mode = 'walking'
                speed = 6.0
                simulate_stops = False
                self.preset_combo.setCurrentIndex(1)  # Switch to walking visually
            else:  # Drive
                transport_mode = 'driving'
                speed = 50.0
                simulate_stops = True
                self.preset_combo.setCurrentIndex(3)  # Switch to drive visually
                self.stops_checkbox.setChecked(True)
        else:
            transport_mode = self._get_transport_mode()
            speed = self.speed_slider.value() / 10.0
            simulate_stops = self.stops_checkbox.isChecked()
            
        interval = self.interval_input.value()

        self.walk_simulation_requested.emit(
            start_lat, start_lon, end_lat, end_lon, speed, interval, simulate_stops, transport_mode
        )
    
    def _on_stop(self):
        self.stop_requested.emit()
        
    def _on_clear(self):
        self.clear_requested.emit()
        
    def _on_freeze(self):
        self.freeze_requested.emit()
        
    def _on_radius_changed(self, value):
        if value >= 1000:
            self.radius_label.setText(f"{value/1000:.1f} km")
        else:
            self.radius_label.setText(f"{value} m")
        self.roam_radius_changed.emit(self.lat_input.value(), self.lon_input.value(), float(value))

    def _on_start_roaming(self):
        lat = self.lat_input.value()
        lon = self.lon_input.value()
        radius = float(self.radius_slider.value())
        duration = self.duration_input.value()
        speed = self.speed_slider.value() / 10.0
        mode = self._get_transport_mode()
        self.roam_requested.emit(lat, lon, radius, duration, speed, mode)
        
    def set_coordinates(self, latitude: float, longitude: float):
        """Set start coordinates from external source (map click, etc.)"""
        self.lat_input.setValue(latitude)
        self.lon_input.setValue(longitude)

    def set_end_location(self, latitude: float, longitude: float):
        """Set destination coordinates from external source (map right-click, etc.)"""
        self.end_lat_input.setValue(latitude)
        self.end_lon_input.setValue(longitude)

    def set_freeze_state(self, is_frozen: bool, can_unfreeze: bool = False):
        """
        Update the freeze button text, stylesheet and enabled state based on application state.
        """
        if is_frozen:
            if can_unfreeze:
                self.freeze_btn.setText("🔓 Unfreeze GPS")
                self.freeze_btn.setEnabled(True)
                self.freeze_btn.setStyleSheet("background-color: rgba(16, 185, 129, 0.9);")
            else:
                self.freeze_btn.setText("❄️ Location Frozen")
                self.freeze_btn.setEnabled(False)
                self.freeze_btn.setStyleSheet("background-color: rgba(99, 102, 241, 0.5);")
        else:
            self.freeze_btn.setText("❄️ Freeze Location")
            self.freeze_btn.setEnabled(True)
            self.freeze_btn.setStyleSheet("")

    def set_enabled(self, enabled: bool):
        """Enable/disable all controls"""
        self.set_location_btn.setEnabled(enabled)
        self.walk_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self.freeze_btn.setEnabled(enabled)
        self.search_btn.setEnabled(enabled)
        self.dest_search_btn.setEnabled(enabled)
        self.copy_loc_btn.setEnabled(enabled)
        self.btn_up.setEnabled(enabled)
        self.btn_down.setEnabled(enabled)
        self.btn_left.setEnabled(enabled)
        self.btn_right.setEnabled(enabled)
        self.stops_checkbox.setEnabled(enabled)
        self.start_roam_btn.setEnabled(enabled)
        self.stop_roam_btn.setEnabled(enabled)
        self.radius_slider.setEnabled(enabled)
        self.duration_input.setEnabled(enabled)