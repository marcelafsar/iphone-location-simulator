"""
Coordinate Utilities - Marcel Location Simulator
Calculations for distances, bearings, destinations, and interpolation.
Created by Marcel Afsar
"""

import math
from typing import Tuple, List


class CoordinateUtils:
    """Utility class for geographic coordinate calculations"""
    
    # Earth's radius in meters
    EARTH_RADIUS = 6378137
    
    @staticmethod
    def calculate_distance(
        lat1: float, lon1: float, 
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates using the Haversine formula
        
        Args:
            lat1: Latitude of point 1
            lon1: Longitude of point 1
            lat2: Latitude of point 2
            lon2: Longitude of point 2
            
        Returns:
            float: Distance in meters
        """
        # Convert degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Differences in coordinates
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = CoordinateUtils.EARTH_RADIUS * c
        return distance
    
    @staticmethod
    def calculate_bearing(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate the bearing angle from point 1 to point 2
        
        Args:
            lat1: Latitude of point 1
            lon1: Longitude of point 1
            lat2: Latitude of point 2
            lon2: Longitude of point 2
            
        Returns:
            float: Bearing in degrees (0 to 360, where 0 is North, 90 is East)
        """
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlon = lon2_rad - lon1_rad
        
        y = math.sin(dlon) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon))
        
        bearing = math.atan2(y, x)
        bearing_degrees = math.degrees(bearing)
        
        # Normalize to 0-360 degrees
        return (bearing_degrees + 360) % 360
    
    @staticmethod
    def calculate_destination(
        lat: float, lon: float,
        distance: float, bearing: float
    ) -> Tuple[float, float]:
        """
        Calculate target destination coordinates given a starting point, distance, and bearing
        
        Args:
            lat: Starting latitude
            lon: Starting longitude
            distance: Distance in meters
            bearing: Bearing angle in degrees
            
        Returns:
            Tuple[float, float]: (Latitude, Longitude) of destination
        """
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing)
        
        # Angular distance
        angular_distance = distance / CoordinateUtils.EARTH_RADIUS
        
        # New latitude
        lat2_rad = math.asin(
            math.sin(lat_rad) * math.cos(angular_distance) +
            math.cos(lat_rad) * math.sin(angular_distance) * 
            math.cos(bearing_rad)
        )
        
        # New longitude
        lon2_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(angular_distance) * 
            math.cos(lat_rad),
            math.cos(angular_distance) - 
            math.sin(lat_rad) * math.sin(lat2_rad)
        )
        
        return math.degrees(lat2_rad), math.degrees(lon2_rad)
    
    @staticmethod
    def interpolate_points(
        lat1: float, lon1: float,
        lat2: float, lon2: float,
        num_points: int
    ) -> List[Tuple[float, float]]:
        """
        Interpolate coordinates between two points
        
        Args:
            lat1: Latitude of point 1
            lon1: Longitude of point 1
            lat2: Latitude of point 2
            lon2: Longitude of point 2
            num_points: Number of points to generate
            
        Returns:
            List[Tuple[float, float]]: Interpolated coordinates
        """
        if num_points < 2:
            return [(lat1, lon1), (lat2, lon2)]
        
        points = []
        for i in range(num_points):
            t = i / (num_points - 1)
            lat = lat1 + (lat2 - lat1) * t
            lon = lon1 + (lon2 - lon1) * t
            points.append((lat, lon))
        
        return points
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> bool:
        """
        Check if a given coordinate coordinate pair is valid
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            bool: True if coordinates are valid, otherwise False
        """
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    @staticmethod
    def normalize_longitude(lon: float) -> float:
        """
        Normalize longitude to stay within the range [-180, 180]
        
        Args:
            lon: Longitude
            
        Returns:
            float: Normalized longitude
        """
        while lon > 180:
            lon -= 360
        while lon < -180:
            lon += 360
        return lon
    
    @staticmethod
    def format_coordinates(lat: float, lon: float, precision: int = 6) -> str:
        """
        Format coordinates to a standard readable string
        
        Args:
            lat: Latitude
            lon: Longitude
            precision: Decimal precision
            
        Returns:
            str: Formatted coordinates string
        """
        lat_str = f"{lat:.{precision}f}"
        lon_str = f"{lon:.{precision}f}"
        
        lat_dir = "N" if lat >= 0 else "S"
        lon_dir = "E" if lon >= 0 else "W"
        
        return f"{abs(float(lat_str))}{lat_dir}, {abs(float(lon_str))}{lon_dir}"