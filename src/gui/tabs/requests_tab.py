"""
Requests Tab for managing multiple FOIA requests.
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QSplitter, QGroupBox, QLabel, QTextEdit,
    QMessageBox, QLineEdit, QDateEdit, QComboBox, QHeaderView
)

from src.processing.request_manager import RequestManager
from src.models.request import FOIARequest
from src.gui.styles import create_title_label, create_primary_button, create_secondary_button
from src.constants import WIDGET_SPACING, MAIN_LAYOUT_MARGINS


class RequestDetailsPanel(QWidget):
    """Panel for displaying and editing request details"""
    
    def __init__(self):
        super().__init__()
        self._current_request: Optional[FOIARequest] = None
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the details panel UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(WIDGET_SPACING)
        
        # Title
        self.title_label = QLabel("Request Details")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # Request info group
        info_group = QGroupBox("Request Information")
        info_layout = QVBoxLayout()
        
        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter request name...")
        name_layout.addWidget(self.name_edit)
        info_layout.addLayout(name_layout)
        
        # Description field
        desc_label = QLabel("Description:")
        info_layout.addWidget(desc_label)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Enter request description...")
        info_layout.addWidget(self.description_edit)
        
        # FOIA request text
        foia_label = QLabel("FOIA Request Text:")
        info_layout.addWidget(foia_label)
        self.foia_text_edit = QTextEdit()
        self.foia_text_edit.setMaximumHeight(100)
        self.foia_text_edit.setPlaceholderText("Enter the actual FOIA request text...")
        info_layout.addWidget(self.foia_text_edit)
        
        # Status and deadline
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["draft", "processing", "review", "complete"])
        status_layout.addWidget(self.status_combo)
        
        status_layout.addWidget(QLabel("Deadline:"))
        self.deadline_edit = QDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDate(datetime.now().date())
        status_layout.addWidget(self.deadline_edit)
        status_layout.addStretch()
        
        info_layout.addLayout(status_layout)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Statistics group
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_labels = {
            'total': QLabel("Total Documents: 0"),
            'processed': QLabel("Processed: 0"),
            'reviewed': QLabel("Reviewed: 0"),
            'responsive': QLabel("Responsive: 0"),
            'non_responsive': QLabel("Non-Responsive: 0"),
            'uncertain': QLabel("Uncertain: 0")
        }
        
        for label in self.stats_labels.values():
            stats_layout.addWidget(label)
            
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Save button
        self.save_button = create_secondary_button("Save Changes")
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)
        
        layout.addStretch()
        
    def set_request(self, request: Optional[FOIARequest]):
        """Set the current request to display"""
        self._current_request = request
        
        if request:
            self.name_edit.setText(request.name)
            self.description_edit.setText(request.description)
            self.foia_text_edit.setText(request.foia_request_text)
            self.status_combo.setCurrentText(request.status)
            
            if request.deadline:
                self.deadline_edit.setDate(request.deadline.date())
                
            # Update statistics
            summary = request.get_summary()
            self.stats_labels['total'].setText(f"Total Documents: {summary['total_documents']}")
            self.stats_labels['processed'].setText(f"Processed: {summary['processed']}")
            self.stats_labels['reviewed'].setText(f"Reviewed: {summary['reviewed']}")
            self.stats_labels['responsive'].setText(f"Responsive: {summary['responsive']}")
            self.stats_labels['non_responsive'].setText(f"Non-Responsive: {summary['non_responsive']}")
            self.stats_labels['uncertain'].setText(f"Uncertain: {summary['uncertain']}")
            
            self.save_button.setEnabled(True)
        else:
            # Clear all fields
            self.name_edit.clear()
            self.description_edit.clear()
            self.foia_text_edit.clear()
            self.status_combo.setCurrentIndex(0)
            self.deadline_edit.setDate(datetime.now().date())
            
            # Clear statistics
            for label in self.stats_labels.values():
                text = label.text().split(':')[0]
                label.setText(f"{text}: 0")
                
            self.save_button.setEnabled(False)
            
    def get_updated_values(self) -> dict:
        """Get the updated values from the form"""
        return {
            'name': self.name_edit.text(),
            'description': self.description_edit.toPlainText(),
            'foia_request_text': self.foia_text_edit.toPlainText(),
            'status': self.status_combo.currentText(),
            'deadline': datetime.combine(
                self.deadline_edit.date().toPyDate(),
                datetime.min.time()
            )
        }


class RequestsTab(QWidget):
    """Tab for managing multiple FOIA requests"""
    
    # Signals
    request_created = pyqtSignal(str)  # request_id
    request_selected = pyqtSignal(str)  # request_id
    request_deleted = pyqtSignal(str)  # request_id
    
    def __init__(self, request_manager: RequestManager):
        super().__init__()
        self.request_manager = request_manager
        self._setup_ui()
        self._connect_signals()
        self._refresh_table()
        
    def _setup_ui(self):
        """Setup the tab UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*MAIN_LAYOUT_MARGINS)
        layout.setSpacing(WIDGET_SPACING)
        
        # Title
        title = create_title_label("FOIA Requests")
        layout.addWidget(title)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.new_button = create_primary_button("New Request")
        self.edit_button = create_secondary_button("Edit")
        self.delete_button = create_secondary_button("Delete")
        self.set_active_button = create_secondary_button("Set Active")
        
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.set_active_button.setEnabled(False)
        
        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.set_active_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Request table
        self.request_table = QTableWidget()
        self.request_table.setColumnCount(6)
        self.request_table.setHorizontalHeaderLabels([
            "Active", "Name", "Status", "Documents", "Created", "Deadline"
        ])
        
        # Set column widths
        header = self.request_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        
        self.request_table.setColumnWidth(0, 60)
        self.request_table.setColumnWidth(2, 100)
        self.request_table.setColumnWidth(3, 100)
        self.request_table.setColumnWidth(4, 150)
        self.request_table.setColumnWidth(5, 150)
        
        # Enable row selection
        self.request_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.request_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Details panel
        self.details_panel = RequestDetailsPanel()
        
        # Splitter layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.request_table)
        splitter.addWidget(self.details_panel)
        splitter.setSizes([600, 400])
        
        layout.addWidget(splitter)
        
    def _connect_signals(self):
        """Connect UI signals"""
        self.new_button.clicked.connect(self._on_new_request)
        self.edit_button.clicked.connect(self._on_edit_request)
        self.delete_button.clicked.connect(self._on_delete_request)
        self.set_active_button.clicked.connect(self._on_set_active)
        
        self.request_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.request_table.cellDoubleClicked.connect(self._on_double_click)
        
        self.details_panel.save_button.clicked.connect(self._on_save_changes)
        
    def _refresh_table(self):
        """Refresh the request table"""
        requests = self.request_manager.list_requests()
        active_request = self.request_manager.get_active_request()
        
        self.request_table.setRowCount(len(requests))
        
        for row, request in enumerate(requests):
            # Active indicator
            active_item = QTableWidgetItem("✓" if request == active_request else "")
            active_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.request_table.setItem(row, 0, active_item)
            
            # Name
            self.request_table.setItem(row, 1, QTableWidgetItem(request.name))
            
            # Status
            status_item = QTableWidgetItem(request.status)
            self.request_table.setItem(row, 2, status_item)
            
            # Documents
            doc_count = f"{request.processed_documents}/{request.total_documents}"
            self.request_table.setItem(row, 3, QTableWidgetItem(doc_count))
            
            # Created
            created_str = request.created_at.strftime("%Y-%m-%d %H:%M")
            self.request_table.setItem(row, 4, QTableWidgetItem(created_str))
            
            # Deadline
            deadline_str = request.deadline.strftime("%Y-%m-%d") if request.deadline else "-"
            self.request_table.setItem(row, 5, QTableWidgetItem(deadline_str))
            
            # Store request ID in first column
            self.request_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, request.id)
            
    def _on_selection_changed(self):
        """Handle table selection changes"""
        selected_rows = self.request_table.selectionModel().selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            request_id = self.request_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            request = self.request_manager.get_request(request_id)
            
            self.details_panel.set_request(request)
            self.edit_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.set_active_button.setEnabled(True)
        else:
            self.details_panel.set_request(None)
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.set_active_button.setEnabled(False)
            
    def _on_double_click(self, row: int, column: int):
        """Handle double-click on table row"""
        request_id = self.request_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self._on_set_active()
        
    def _on_new_request(self):
        """Create a new request"""
        name, ok = QLineEdit().getText(self, "New Request", "Enter request name:")
        
        if ok and name:
            request = self.request_manager.create_request(name)
            self._refresh_table()
            self.request_created.emit(request.id)
            
            # Select the new request
            for row in range(self.request_table.rowCount()):
                if self.request_table.item(row, 0).data(Qt.ItemDataRole.UserRole) == request.id:
                    self.request_table.selectRow(row)
                    break
                    
    def _on_edit_request(self):
        """Edit the selected request (just enables the save button)"""
        self.details_panel.save_button.setEnabled(True)
        
    def _on_delete_request(self):
        """Delete the selected request"""
        selected_rows = self.request_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        request_id = self.request_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        request = self.request_manager.get_request(request_id)
        
        if not request:
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Request",
            f"Are you sure you want to delete '{request.name}'?\n\n"
            f"This will permanently delete all associated documents and data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.request_manager.delete_request(request_id)
            self._refresh_table()
            self.request_deleted.emit(request_id)
            
    def _on_set_active(self):
        """Set the selected request as active"""
        selected_rows = self.request_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        request_id = self.request_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if self.request_manager.set_active_request(request_id):
            self._refresh_table()
            self.request_selected.emit(request_id)
            
    def _on_save_changes(self):
        """Save changes to the current request"""
        selected_rows = self.request_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        request_id = self.request_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        # Get updated values
        values = self.details_panel.get_updated_values()
        
        # Update request
        if self.request_manager.update_request(request_id, **values):
            self._refresh_table()
            QMessageBox.information(
                self,
                "Success",
                "Request updated successfully."
            )
            self.details_panel.save_button.setEnabled(False)
        else:
            QMessageBox.warning(
                self,
                "Error",
                "Failed to update request."
            )