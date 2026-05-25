"""
ルート生成
"""

from typing import List, Tuple, Optional
from loguru import logger

from core.coordinate_utils import CoordinateUtils


class Route:
    """ルートを表すクラス"""
    
    def __init__(self, name: str = "Untitled Route"):
        self.name = name
        self.waypoints: List[Tuple[float, float]] = []
        self.description: str = ""
    
    def add_waypoint(self, latitude: float, longitude: float):
        """ウェイポイントを追加"""
        if CoordinateUtils.validate_coordinates(latitude, longitude):
            self.waypoints.append((latitude, longitude))
            logger.debug(f"ウェイポイント追加: ({latitude}, {longitude})")
        else:
            logger.warning(f"無効な座標: ({latitude}, {longitude})")
    
    def remove_waypoint(self, index: int):
        """指定したインデックスのウェイポイントを削除"""
        if 0 <= index < len(self.waypoints):
            removed = self.waypoints.pop(index)
            logger.debug(f"ウェイポイント削除: {removed}")
    
    def clear_waypoints(self):
        """全てのウェイポイントをクリア"""
        self.waypoints.clear()
        logger.debug("全てのウェイポイントをクリアしました")
    
    def get_total_distance(self) -> float:
        """
        ルートの全体距離を計算
        
        Returns:
            float: 距離（メートル）
        """
        if len(self.waypoints) < 2:
            return 0.0
        
        total = 0.0
        for i in range(len(self.waypoints) - 1):
            lat1, lon1 = self.waypoints[i]
            lat2, lon2 = self.waypoints[i + 1]
            total += CoordinateUtils.calculate_distance(lat1, lon1, lat2, lon2)
        
        return total
    
    def to_dict(self) -> dict:
        """ルートを辞書に変換"""
        return {
            'name': self.name,
            'description': self.description,
            'waypoints': [
                {'latitude': lat, 'longitude': lon}
                for lat, lon in self.waypoints
            ],
            'total_distance': self.get_total_distance()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Route':
        """辞書からルートを作成"""
        route = cls(data.get('name', 'Untitled Route'))
        route.description = data.get('description', '')
        
        for wp in data.get('waypoints', []):
            route.add_waypoint(wp['latitude'], wp['longitude'])
        
        return route


class RouteGenerator:
    """ルート生成のためのユーティリティクラス"""
    
    @staticmethod
    def generate_circular_route(
        center_lat: float,
        center_lon: float,
        radius_meters: float,
        num_points: int = 8
    ) -> Route:
        """
        円形のルートを生成
        
        Args:
            center_lat: 中心の緯度
            center_lon: 中心の経度
            radius_meters: 半径（メートル）
            num_points: ウェイポイントの数
            
        Returns:
            Route: 生成されたルート
        """
        route = Route(f"円形ルート (半径{radius_meters}m)")
        
        for i in range(num_points):
            angle = (360 / num_points) * i
            lat, lon = CoordinateUtils.calculate_destination(
                center_lat, center_lon, radius_meters, angle
            )
            route.add_waypoint(lat, lon)
        
        # 最初の点に戻って円を閉じる
        if route.waypoints:
            route.add_waypoint(route.waypoints[0][0], route.waypoints[0][1])
        
        logger.info(f"円形ルートを生成: {num_points}ポイント, 半径{radius_meters}m")
        return route
    
    @staticmethod
    def generate_grid_route(
        start_lat: float,
        start_lon: float,
        grid_size: int = 3,
        spacing_meters: float = 100
    ) -> Route:
        """
        グリッド状のルートを生成
        
        Args:
            start_lat: 開始地点の緯度
            start_lon: 開始地点の経度
            grid_size: グリッドのサイズ（N x N）
            spacing_meters: グリッド間隔（メートル）
            
        Returns:
            Route: 生成されたルート
        """
        route = Route(f"グリッドルート ({grid_size}x{grid_size})")
        
        current_lat, current_lon = start_lat, start_lon
        
        for row in range(grid_size):
            if row % 2 == 0:
                # 左から右
                for col in range(grid_size):
                    route.add_waypoint(current_lat, current_lon)
                    if col < grid_size - 1:
                        current_lat, current_lon = CoordinateUtils.calculate_destination(
                            current_lat, current_lon, spacing_meters, 90
                        )
            else:
                # 右から左
                for col in range(grid_size):
                    route.add_waypoint(current_lat, current_lon)
                    if col < grid_size - 1:
                        current_lat, current_lon = CoordinateUtils.calculate_destination(
                            current_lat, current_lon, spacing_meters, 270
                        )
            
            # 次の行へ
            if row < grid_size - 1:
                current_lat, current_lon = CoordinateUtils.calculate_destination(
                    current_lat, current_lon, spacing_meters, 180
                )
        
        logger.info(f"グリッドルートを生成: {grid_size}x{grid_size}, 間隔{spacing_meters}m")
        return route
    
    @staticmethod
    def generate_random_walk(
        start_lat: float,
        start_lon: float,
        num_steps: int = 10,
        step_distance: float = 50,
        seed: Optional[int] = None
    ) -> Route:
        """
        ランダムウォークのルートを生成
        
        Args:
            start_lat: 開始地点の緯度
            start_lon: 開始地点の経度
            num_steps: ステップ数
            step_distance: 各ステップの距離（メートル）
            seed: 乱数シード
            
        Returns:
            Route: 生成されたルート
        """
        import random
        if seed is not None:
            random.seed(seed)
        
        route = Route(f"ランダムウォーク ({num_steps}ステップ)")
        
        current_lat, current_lon = start_lat, start_lon
        route.add_waypoint(current_lat, current_lon)
        
        for _ in range(num_steps):
            # ランダムな方角
            bearing = random.uniform(0, 360)
            # ランダムな距離（指定距離の50%〜150%）
            distance = random.uniform(step_distance * 0.5, step_distance * 1.5)
            
            current_lat, current_lon = CoordinateUtils.calculate_destination(
                current_lat, current_lon, distance, bearing
            )
            route.add_waypoint(current_lat, current_lon)
        
        logger.info(f"ランダムウォークを生成: {num_steps}ステップ")
        return route
    
    @staticmethod
    def interpolate_route(
        route: Route,
        max_distance_between_points: float = 10
    ) -> Route:
        """
        ルートのウェイポイント間を補間して滑らかにする
        
        Args:
            route: 元のルート
            max_distance_between_points: ポイント間の最大距離（メートル）
            
        Returns:
            Route: 補間されたルート
        """
        interpolated = Route(f"{route.name} (補間)")
        interpolated.description = route.description
        
        if len(route.waypoints) < 2:
            return route
        
        for i in range(len(route.waypoints) - 1):
            lat1, lon1 = route.waypoints[i]
            lat2, lon2 = route.waypoints[i + 1]
            
            distance = CoordinateUtils.calculate_distance(lat1, lon1, lat2, lon2)
            num_interpolated = max(2, int(distance / max_distance_between_points))
            
            points = CoordinateUtils.interpolate_points(
                lat1, lon1, lat2, lon2, num_interpolated
            )
            
            for lat, lon in points[:-1]:  # 最後の点は次のセグメントの始点
                interpolated.add_waypoint(lat, lon)
        
        # 最後の点を追加
        interpolated.add_waypoint(route.waypoints[-1][0], route.waypoints[-1][1])
        
        logger.info(
            f"ルートを補間: {len(route.waypoints)}点 → {len(interpolated.waypoints)}点"
        )
        return interpolated
    
    @staticmethod
    def simplify_route(
        route: Route,
        tolerance_meters: float = 5
    ) -> Route:
        """
        ルートを簡略化（Douglas-Peuckerアルゴリズム風）
        
        Args:
            route: 元のルート
            tolerance_meters: 許容誤差（メートル）
            
        Returns:
            Route: 簡略化されたルート
        """
        if len(route.waypoints) <= 2:
            return route
        
        simplified = Route(f"{route.name} (簡略)")
        simplified.description = route.description
        
        # 簡易版: 一定距離以内の点をスキップ
        simplified.add_waypoint(route.waypoints[0][0], route.waypoints[0][1])
        
        last_added = 0
        for i in range(1, len(route.waypoints) - 1):
            lat1, lon1 = route.waypoints[last_added]
            lat2, lon2 = route.waypoints[i]
            
            distance = CoordinateUtils.calculate_distance(lat1, lon1, lat2, lon2)
            
            if distance >= tolerance_meters:
                simplified.add_waypoint(lat2, lon2)
                last_added = i
        
        # 最後の点を追加
        simplified.add_waypoint(
            route.waypoints[-1][0],
            route.waypoints[-1][1]
        )
        
        logger.info(
            f"ルートを簡略化: {len(route.waypoints)}点 → {len(simplified.waypoints)}点"
        )
        return simplified