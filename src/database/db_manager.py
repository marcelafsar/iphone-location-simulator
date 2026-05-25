"""
Database Manager - Marcel Location Simulator
SQLite database management for saving locations and routes.
Created by Marcel Afsar
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

Base = declarative_base()


class FavoriteLocation(Base):
    """Model representing a saved favorite location"""
    __tablename__ = 'favorite_locations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    category = Column(String(100), default='Uncategorized')
    description = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert object fields to a dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'category': self.category,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SavedRoute(Base):
    """Model representing a saved simulation route"""
    __tablename__ = 'saved_routes'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default='')
    waypoints_json = Column(Text, nullable=False)  # JSON formatted string
    total_distance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert object fields to a dictionary"""
        import json
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'waypoints': json.loads(self.waypoints_json),
            'total_distance': self.total_distance,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DatabaseManager:
    """Manages SQLite database sessions and CRUD operations"""
    
    def __init__(self, db_path: str = "data/favorites.db"):
        """
        Args:
            db_path: Path to SQLite database file
        """
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to DB
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info(f"Database initialized at: {db_path}")
    
    def get_session(self) -> Session:
        """Retrieve a new database session"""
        return self.SessionLocal()
    
    # ----------------------------
    # Favorite Locations CRUD
    # ----------------------------
    
    def add_favorite(
        self,
        name: str,
        latitude: float,
        longitude: float,
        category: str = 'Uncategorized',
        description: str = ''
    ) -> Optional[FavoriteLocation]:
        """
        Save a new location to favorites
        
        Args:
            name: Location name
            latitude: Latitude
            longitude: Longitude
            category: Custom category tag
            description: Short text description
            
        Returns:
            FavoriteLocation: The added object, or None if failed
        """
        session = self.get_session()
        try:
            favorite = FavoriteLocation(
                name=name,
                latitude=latitude,
                longitude=longitude,
                category=category,
                description=description
            )
            session.add(favorite)
            session.commit()
            session.refresh(favorite)
            logger.info(f"Favorite location added: {name}")
            return favorite
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding favorite: {e}")
            return None
        finally:
            session.close()
    
    def get_favorite(self, favorite_id: int) -> Optional[FavoriteLocation]:
        """Retrieve favorite details by ID"""
        session = self.get_session()
        try:
            return session.query(FavoriteLocation).filter_by(id=favorite_id).first()
        finally:
            session.close()
    
    def get_all_favorites(self, category: Optional[str] = None) -> List[FavoriteLocation]:
        """Retrieve list of all favorites, optional filter by category"""
        session = self.get_session()
        try:
            query = session.query(FavoriteLocation)
            if category:
                query = query.filter_by(category=category)
            return query.order_by(FavoriteLocation.created_at.desc()).all()
        finally:
            session.close()
    
    def search_favorites(self, keyword: str) -> List[FavoriteLocation]:
        """Search favorites matching a keyword"""
        session = self.get_session()
        try:
            return session.query(FavoriteLocation).filter(
                FavoriteLocation.name.like(f'%{keyword}%')
            ).all()
        finally:
            session.close()
    
    def update_favorite(
        self,
        favorite_id: int,
        name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        category: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """Update fields of an existing favorite location"""
        session = self.get_session()
        try:
            favorite = session.query(FavoriteLocation).filter_by(id=favorite_id).first()
            if not favorite:
                return False
            
            if name is not None:
                favorite.name = name
            if latitude is not None:
                favorite.latitude = latitude
            if longitude is not None:
                favorite.longitude = longitude
            if category is not None:
                favorite.category = category
            if description is not None:
                favorite.description = description
            
            favorite.updated_at = datetime.now()
            session.commit()
            logger.info(f"Favorite updated: ID={favorite_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating favorite: {e}")
            return False
        finally:
            session.close()
    
    def delete_favorite(self, favorite_id: int) -> bool:
        """Remove a location from favorites"""
        session = self.get_session()
        try:
            favorite = session.query(FavoriteLocation).filter_by(id=favorite_id).first()
            if not favorite:
                return False
            
            session.delete(favorite)
            session.commit()
            logger.info(f"Favorite deleted: ID={favorite_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting favorite: {e}")
            return False
        finally:
            session.close()
    
    def get_categories(self) -> List[str]:
        """Get unique category list"""
        session = self.get_session()
        try:
            categories = session.query(FavoriteLocation.category).distinct().all()
            return [cat[0] for cat in categories]
        finally:
            session.close()
    
    # ----------------------------
    # Saved Routes CRUD
    # ----------------------------
    
    def add_route(
        self,
        name: str,
        waypoints: List[dict],
        total_distance: float = 0.0,
        description: str = ''
    ) -> Optional[SavedRoute]:
        """Save a new path route"""
        import json
        session = self.get_session()
        try:
            route = SavedRoute(
                name=name,
                description=description,
                waypoints_json=json.dumps(waypoints, ensure_ascii=False),
                total_distance=total_distance
            )
            session.add(route)
            session.commit()
            session.refresh(route)
            logger.info(f"Route saved: {name}")
            return route
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving route: {e}")
            return None
        finally:
            session.close()
    
    def get_route(self, route_id: int) -> Optional[SavedRoute]:
        """Retrieve path route by ID"""
        session = self.get_session()
        try:
            return session.query(SavedRoute).filter_by(id=route_id).first()
        finally:
            session.close()
    
    def get_all_routes(self) -> List[SavedRoute]:
        """Retrieve list of all saved routes"""
        session = self.get_session()
        try:
            return session.query(SavedRoute).order_by(
                SavedRoute.created_at.desc()
            ).all()
        finally:
            session.close()
    
    def delete_route(self, route_id: int) -> bool:
        """Remove a saved path route"""
        session = self.get_session()
        try:
            route = session.query(SavedRoute).filter_by(id=route_id).first()
            if not route:
                return False
            
            session.delete(route)
            session.commit()
            logger.info(f"Route deleted: ID={route_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting route: {e}")
            return False
        finally:
            session.close()