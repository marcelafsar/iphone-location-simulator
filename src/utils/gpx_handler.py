"""
GPXファイル処理
"""

from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime
import gpxpy
import gpxpy.gpx
from loguru import logger

from core.route_generator import Route


class GPXHandler:
    """GPXファイルの読み込み・書き込みを処理するクラス"""
    
    @staticmethod
    def import_gpx(file_path: str) -> Optional[Route]:
        """
        GPXファイルからルートをインポート
        
        Args:
            file_path: GPXファイルのパス
            
        Returns:
            Route: インポートされたルート、失敗時None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)
            
            route = Route(name=Path(file_path).stem)
            
            # トラックから座標を取得
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        route.add_waypoint(point.latitude, point.longitude)
            
            # ルートから座標を取得（トラックがない場合）
            if len(route.waypoints) == 0:
                for gpx_route in gpx.routes:
                    for point in gpx_route.points:
                        route.add_waypoint(point.latitude, point.longitude)
            
            # ウェイポイントから座標を取得（他がない場合）
            if len(route.waypoints) == 0:
                for waypoint in gpx.waypoints:
                    route.add_waypoint(waypoint.latitude, waypoint.longitude)
            
            if len(route.waypoints) > 0:
                logger.info(
                    f"GPXファイルをインポート: {file_path}, "
                    f"{len(route.waypoints)}ポイント"
                )
                return route
            else:
                logger.warning(f"GPXファイルに座標データが見つかりません: {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"GPXインポートエラー: {e}")
            return None
    
    @staticmethod
    def export_gpx(
        route: Route,
        file_path: str,
        add_timestamps: bool = False,
        time_interval_seconds: int = 1
    ) -> bool:
        """
        ルートをGPXファイルにエクスポート
        
        Args:
            route: エクスポートするルート
            file_path: 保存先のファイルパス
            add_timestamps: タイムスタンプを追加するか
            time_interval_seconds: ポイント間の時間間隔（秒）
            
        Returns:
            bool: 成功時True
        """
        try:
            # GPXオブジェクトを作成
            gpx = gpxpy.gpx.GPX()
            
            # トラックを作成
            gpx_track = gpxpy.gpx.GPXTrack()
            gpx_track.name = route.name
            if route.description:
                gpx_track.description = route.description
            gpx.tracks.append(gpx_track)
            
            # セグメントを作成
            gpx_segment = gpxpy.gpx.GPXTrackSegment()
            gpx_track.segments.append(gpx_segment)
            
            # ウェイポイントを追加
            current_time = datetime.now()
            for i, (lat, lon) in enumerate(route.waypoints):
                point = gpxpy.gpx.GPXTrackPoint(lat, lon)
                
                if add_timestamps:
                    point.time = current_time
                    from datetime import timedelta
                    current_time += timedelta(seconds=time_interval_seconds)
                
                gpx_segment.points.append(point)
            
            # ファイルに書き込み
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(gpx.to_xml())
            
            logger.info(f"GPXファイルをエクスポート: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"GPXエクスポートエラー: {e}")
            return False
    
    @staticmethod
    def get_gpx_info(file_path: str) -> Optional[dict]:
        """
        GPXファイルの情報を取得
        
        Args:
            file_path: GPXファイルのパス
            
        Returns:
            dict: ファイル情報、失敗時None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)
            
            total_points = 0
            total_distance = 0.0
            
            for track in gpx.tracks:
                for segment in track.segments:
                    total_points += len(segment.points)
                    total_distance += segment.length_2d() or 0.0
            
            return {
                'name': Path(file_path).stem,
                'total_points': total_points,
                'total_distance': total_distance,
                'num_tracks': len(gpx.tracks),
                'num_routes': len(gpx.routes),
                'num_waypoints': len(gpx.waypoints)
            }
            
        except Exception as e:
            logger.error(f"GPX情報取得エラー: {e}")
            return None
    
    @staticmethod
    def merge_gpx_files(file_paths: List[str], output_path: str) -> bool:
        """
        複数のGPXファイルを結合
        
        Args:
            file_paths: 結合するGPXファイルのリスト
            output_path: 出力ファイルのパス
            
        Returns:
            bool: 成功時True
        """
        try:
            merged_gpx = gpxpy.gpx.GPX()
            merged_track = gpxpy.gpx.GPXTrack()
            merged_track.name = "Merged Track"
            merged_gpx.tracks.append(merged_track)
            
            for file_path in file_paths:
                with open(file_path, 'r', encoding='utf-8') as f:
                    gpx = gpxpy.parse(f)
                
                for track in gpx.tracks:
                    for segment in track.segments:
                        merged_track.segments.append(segment)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(merged_gpx.to_xml())
            
            logger.info(f"GPXファイルを結合: {len(file_paths)}ファイル → {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"GPX結合エラー: {e}")
            return False
    
    @staticmethod
    def simplify_gpx(
        input_path: str,
        output_path: str,
        max_distance: float = 10.0
    ) -> bool:
        """
        GPXファイルを簡略化
        
        Args:
            input_path: 入力GPXファイル
            output_path: 出力GPXファイル
            max_distance: 簡略化の距離閾値（メートル）
            
        Returns:
            bool: 成功時True
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)
            
            # 全トラックを簡略化
            for track in gpx.tracks:
                for segment in track.segments:
                    segment.simplify(max_distance=max_distance)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(gpx.to_xml())
            
            logger.info(f"GPXファイルを簡略化: {input_path} → {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"GPX簡略化エラー: {e}")
            return False