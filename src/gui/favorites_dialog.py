"""
Favorites Dialog - Marcel Location Simulator
Manage favorite saved locations and categories in English.
Created by Marcel Afsar
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
    QComboBox, QMessageBox, QHeaderView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger

from database.db_manager import DatabaseManager


class FavoritesDialog(QDialog):
    """Favorites Management Dialog"""
    
    # Signal: emits (latitude, longitude, name)
    favorite_selected = pyqtSignal(float, float, str)
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        
        self.db_manager = db_manager
        
        self.setWindowTitle("Saved Favorites")
        self.setMinimumSize(800, 600)
        
        self._init_ui()
        self._load_favorites()
    
    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Search and Category filter bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name...")
        self.search_input.textChanged.connect(self._filter_favorites)
        search_layout.addWidget(self.search_input)
        
        search_layout.addWidget(QLabel("Category:"))
        self.category_filter = QComboBox()
        self.category_filter.addItem("All")
        self.category_filter.currentTextChanged.connect(self._filter_favorites)
        search_layout.addWidget(self.category_filter)
        
        layout.addLayout(search_layout)
        
        # Favorites Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Latitude", "Longitude", "Category", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._on_favorite_double_clicked)
        layout.addWidget(self.table)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add New")
        self.add_btn.clicked.connect(self._add_favorite)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_favorite)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_favorite)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _load_favorites(self):
        """Load favorite locations from database"""
        # Update categories list
        categories = self.db_manager.get_categories()
        current_category = self.category_filter.currentText()
        self.category_filter.clear()
        self.category_filter.addItem("All")
        self.category_filter.addItems(categories)
        
        # Restore previously selected category
        index = self.category_filter.findText(current_category)
        if index >= 0:
            self.category_filter.setCurrentIndex(index)
        
        # Retrieve favorites
        category = None if self.category_filter.currentText() == "All" else self.category_filter.currentText()
        favorites = self.db_manager.get_all_favorites(category=category)
        
        # Clear table
        self.table.setRowCount(0)
        
        # Populate table
        for favorite in favorites:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(favorite.name))
            self.table.setItem(row, 1, QTableWidgetItem(f"{favorite.latitude:.6f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{favorite.longitude:.6f}"))
            self.table.setItem(row, 3, QTableWidgetItem(favorite.category))
            self.table.setItem(row, 4, QTableWidgetItem(favorite.description or ""))
            
            # Store ID in UserRole data
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, favorite.id)
        
        logger.debug(f"Loaded {len(favorites)} saved favorites")
    
    def _filter_favorites(self):
        """Filter favorites table based on search input and selected category"""
        search_text = self.search_input.text().lower()
        
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().lower()
            category = self.table.item(row, 3).text()
            
            # Category match
            category_match = (
                self.category_filter.currentText() == "All" or
                category == self.category_filter.currentText()
            )
            
            # Search text match
            text_match = search_text in name
            
            self.table.setRowHidden(row, not (category_match and text_match))
    
    def _show_context_menu(self, position):
        """Display right-click context menu"""
        menu = QMenu()
        
        select_action = menu.addAction("Go to this location")
        edit_action = menu.addAction("Edit details")
        delete_action = menu.addAction("Delete favorite")
        
        action = menu.exec(self.table.mapToGlobal(position))
        
        if action == select_action:
            self._on_favorite_double_clicked(self.table.currentRow(), 0)
        elif action == edit_action:
            self._edit_favorite()
        elif action == delete_action:
            self._delete_favorite()
    
    def _on_favorite_double_clicked(self, row: int, column: int):
        """Handle favorite location selection on double click"""
        if row < 0:
            return
        
        name = self.table.item(row, 0).text()
        lat = float(self.table.item(row, 1).text())
        lon = float(self.table.item(row, 2).text())
        
        self.favorite_selected.emit(lat, lon, name)
        logger.info(f"Favorite selected: {name} ({lat}, {lon})")
        self.accept()
    
    def _add_favorite(self):
        """Open dialog to add a new favorite location"""
        dialog = AddFavoriteDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_favorites()
    
    def _edit_favorite(self):
        """Open dialog to edit the selected favorite location"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a location to edit.")
            return
        
        favorite_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        dialog = AddFavoriteDialog(self.db_manager, self, favorite_id=favorite_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_favorites()
    
    def _delete_favorite(self):
        """Delete the selected favorite location"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Please select a location to delete.")
            return
        
        name = self.table.item(row, 0).text()
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            favorite_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if self.db_manager.delete_favorite(favorite_id):
                self._load_favorites()
                logger.info(f"Deleted favorite: {name}")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete location.")


class AddFavoriteDialog(QDialog):
    """Dialog to add or edit favorite locations"""
    
    def __init__(self, db_manager: DatabaseManager, parent=None, favorite_id: int = None):
        super().__init__(parent)
        
        self.db_manager = db_manager
        self.favorite_id = favorite_id
        
        self.setWindowTitle("Edit Favorite" if favorite_id else "Add Favorite")
        self.setMinimumWidth(400)
        
        self._init_ui()
        
        if favorite_id:
            self._load_favorite()
    
    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Name
        layout.addWidget(QLabel("Name:"))
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)
        
        # Latitude
        layout.addWidget(QLabel("Latitude:"))
        self.lat_input = QLineEdit()
        layout.addWidget(self.lat_input)
        
        # Longitude
        layout.addWidget(QLabel("Longitude:"))
        self.lon_input = QLineEdit()
        layout.addWidget(self.lon_input)
        
        # Category
        layout.addWidget(QLabel("Category:"))
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.addItems(self.db_manager.get_categories())
        layout.addWidget(self.category_input)
        
        # Description
        layout.addWidget(QLabel("Description:"))
        self.description_input = QLineEdit()
        layout.addWidget(self.description_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _load_favorite(self):
        """Load favorite details into the inputs"""
        favorite = self.db_manager.get_favorite(self.favorite_id)
        if favorite:
            self.name_input.setText(favorite.name)
            self.lat_input.setText(str(favorite.latitude))
            self.lon_input.setText(str(favorite.longitude))
            self.category_input.setCurrentText(favorite.category)
            self.description_input.setText(favorite.description or "")
    
    def _save(self):
        """Validate and save favorite location details"""
        from utils.validators import Validators
        
        name = self.name_input.text().strip()
        try:
            lat = float(self.lat_input.text().strip())
            lon = float(self.lon_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Error", "Latitude and Longitude must be numeric values.")
            return
        
        category = self.category_input.currentText().strip() or "Uncategorized"
        description = self.description_input.text().strip()
        
        # Validations
        valid_name, msg_name = Validators.validate_name(name)
        if not valid_name:
            QMessageBox.warning(self, "Error", msg_name)
            return
        
        valid_coords, msg_coords = Validators.validate_coordinates(lat, lon)
        if not valid_coords:
            QMessageBox.warning(self, "Error", msg_coords)
            return
        
        # Save to DB
        if self.favorite_id:
            success = self.db_manager.update_favorite(
                self.favorite_id, name, lat, lon, category, description
            )
        else:
            result = self.db_manager.add_favorite(name, lat, lon, category, description)
            success = result is not None
        
        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save favorite location.")