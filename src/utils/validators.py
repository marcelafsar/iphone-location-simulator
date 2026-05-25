"""
Input Validation Utilities - Marcel Location Simulator
Validate and sanitize geographic values, speed, updates, files, and names.
Created by Marcel Afsar
"""

import re
from typing import Tuple, Optional


class Validators:
    """Helper class to validate and sanitize user inputs"""
    
    @staticmethod
    def validate_latitude(lat: float) -> Tuple[bool, str]:
        """
        Validate latitude coordinates
        
        Args:
            lat: Latitude
            
        Returns:
            Tuple[bool, str]: (isValid, errorMessage)
        """
        if not isinstance(lat, (int, float)):
            return False, "Latitude must be a numeric value"
        
        if not -90 <= lat <= 90:
            return False, "Latitude must be in the range of -90 to 90"
        
        return True, ""
    
    @staticmethod
    def validate_longitude(lon: float) -> Tuple[bool, str]:
        """
        Validate longitude coordinates
        
        Args:
            lon: Longitude
            
        Returns:
            Tuple[bool, str]: (isValid, errorMessage)
        """
        if not isinstance(lon, (int, float)):
            return False, "Longitude must be a numeric value"
        
        if not -180 <= lon <= 180:
            return False, "Longitude must be in the range of -180 to 180"
        
        return True, ""
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> Tuple[bool, str]:
        """
        Validate latitude and longitude pairs
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Tuple[bool, str]: (isValid, errorMessage)
        """
        valid_lat, msg_lat = Validators.validate_latitude(lat)
        if not valid_lat:
            return False, msg_lat
        
        valid_lon, msg_lon = Validators.validate_longitude(lon)
        if not valid_lon:
            return False, msg_lon
        
        return True, ""
    
    @staticmethod
    def validate_speed(speed: float, min_speed: float = 0.1, max_speed: float = 100.0) -> Tuple[bool, str]:
        """
        Validate target speed input
        
        Args:
            speed: Speed in km/h
            min_speed: Minimum allowed speed
            max_speed: Maximum allowed speed
            
        Returns:
            Tuple[bool, str]: (isValid, errorMessage)
        """
        if not isinstance(speed, (int, float)):
            return False, "Speed must be a numeric value"
        
        if not min_speed <= speed <= max_speed:
            return False, f"Speed must be between {min_speed} and {max_speed} km/h"
        
        return True, ""
    
    @staticmethod
    def validate_update_interval(interval: float) -> Tuple[bool, str]:
        """
        Validate interval updates
        
        Args:
            interval: Update interval in seconds
            
        Returns:
            Tuple[bool, str]: (isValid, errorMessage)
        """
        if not isinstance(interval, (int, float)):
            return False, "Update interval must be a numeric value"
        
        if interval <= 0:
            return False, "Update interval must be a positive value"
        
        if interval > 60:
            return False, "Update interval must be less than 60 seconds"
        
        return True, ""
    
    @staticmethod
    def validate_distance(distance: float) -> Tuple[bool, str]:
        """
        Validate path distances
        
        Args:
            distance: Distance in meters
            
        Returns:
            Tuple[bool, str]: (isValid, errorMessage)
        """
        if not isinstance(distance, (int, float)):
            return False, "Distance must be a numeric value"
        
        if distance < 0:
            return False, "Distance must be greater than or equal to 0"
        
        if distance > 100000:  # 100km limit
            return False, "Distance must be less than 100 km"
        
        return True, ""
    
    @staticmethod
    def validate_name(name: str, max_length: int = 200) -> Tuple[bool, str]:
        """
        Validate input name text
        
        Args:
            name: Input string
            max_length: Maximum allowed string length
            
        Returns:
            Tuple[bool, str]: (isValid, errorMessage)
        """
        if not isinstance(name, str):
            return False, "Name must be a string value"
        
        if len(name.strip()) == 0:
            return False, "Name cannot be empty"
        
        if len(name) > max_length:
            return False, f"Name must be less than {max_length} characters"
        
        return True, ""
    
    @staticmethod
    def parse_coordinates_string(coord_str: str) -> Optional[Tuple[float, float]]:
        """
        Parse raw coordinate strings
        
        Args:
            coord_str: Coordinate string (e.g. "35.6812, 139.7671" or "35.6812N, 139.7671E")
            
        Returns:
            Tuple[float, float]: parsed (latitude, longitude), or None if parsing failed
        """
        try:
            parts = coord_str.strip().replace(' ', '').split(',')
            if len(parts) != 2:
                return None
            
            lat_str = re.sub(r'[NSns]', '', parts[0])
            lon_str = re.sub(r'[EWew]', '', parts[1])
            
            lat = float(lat_str)
            lon = float(lon_str)
            
            if 'S' in parts[0].upper():
                lat = -abs(lat)
            
            if 'W' in parts[1].upper():
                lon = -abs(lon)
            
            valid, _ = Validators.validate_coordinates(lat, lon)
            if not valid:
                return None
            
            return lat, lon
            
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def validate_file_path(file_path: str, extensions: list = None) -> Tuple[bool, str]:
        """
        Validate local file paths
        
        Args:
            file_path: Local file path string
            extensions: Allowed extension list (e.g. ['.gpx', '.json'])
            
        Returns:
            Tuple[bool, str]: (isValid, errorMessage)
        """
        from pathlib import Path
        
        if not isinstance(file_path, str):
            return False, "File path must be a string value"
        
        path = Path(file_path)
        
        if not path.exists():
            return False, "File does not exist"
        
        if not path.is_file():
            return False, "Path does not point to a valid file"
        
        if extensions:
            if path.suffix.lower() not in [ext.lower() for ext in extensions]:
                return False, f"Allowed extensions: {', '.join(extensions)}"
        
        return True, ""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize raw filenames to stay safe for the OS
        
        Args:
            filename: Original filename
            
        Returns:
            str: Sanitized safe filename
        """
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '_', filename)
        
        sanitized = sanitized.strip('. ')
        
        if not sanitized:
            sanitized = 'untitled'
        
        return sanitized