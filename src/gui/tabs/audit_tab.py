"""
Audit Tab for FOIA Response Assistant

Provides a document-based audit trail viewer with per-document audit history.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
    QLabel, QFileDialog, QMessageBox, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QLineEdit, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from ...processing.audit_manager import AuditManager
from ...constants import BUTTON_STYLE_PRIMARY, TABLE_CHECKBOX_COLUMN_WIDTH
from ..styles import create_title_label
from ...processing.document_store import DocumentStore
from ...processing.request_manager import RequestManager


class AuditTab(QWidget):
    """Document-based audit trail viewer and export interface."""
    
    def __init__(self, audit_manager: AuditManager, request_manager: RequestManager | None = None, document_store: DocumentStore | None = None):
        super().__init__()
        self.audit_manager = audit_manager
        self.request_manager = request_manager
        self.document_store = document_store
        self.current_document = None
        self.documents_with_audits = []  # List of documents that have audit entries
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the audit tab user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header section
        header_layout = QHBoxLayout()
        
        # Title
        title_label = create_title_label("Audits")
        
        # Active request display
        self.active_request_label = QLabel("No active request")
        self.active_request_label.setStyleSheet("color: #666666; font-size: 12px; font-style: italic;")
        
        # Export button
        self.export_button = QPushButton("Export Audit")
        self.export_button.setStyleSheet(BUTTON_STYLE_PRIMARY)
        self.export_button.clicked.connect(self._export_audit)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.active_request_label)
        header_layout.addStretch()
        header_layout.addWidget(self.export_button)
        
        layout.addLayout(header_layout)
        
        # Search and filter controls
        controls_layout = QHBoxLayout()
        
        # Search box
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search documents...")
        self.search_input.textChanged.connect(self.apply_filters)
        
        controls_layout.addWidget(search_label)
        controls_layout.addWidget(self.search_input)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Document table
        left_panel = self._create_document_panel()
        splitter.addWidget(left_panel)
        
        # Right side - Audit display for selected document
        right_panel = self._create_audit_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions (50% documents, 50% audit)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        
        layout.addWidget(splitter)
        
        # Refresh the display and active request context
        self._update_active_request_display()
        self.refresh()
    
    def _create_document_panel(self) -> QWidget:
        """Create the left panel with document table."""
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Document table
        self.document_table = QTableWidget()
        self.document_table.setColumnCount(5)
        self.document_table.setHorizontalHeaderLabels(
            ["Document", "AI Class", "Human Decision", "Audit Events", "Last Activity"]
        )
        self.document_table.setSortingEnabled(True)
        self.document_table.setAlternatingRowColors(True)
        self.document_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.document_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.document_table.itemSelectionChanged.connect(self._on_document_selected)
        
        # Set size policy and make filename column stretch
        self.document_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.document_table.horizontalHeader().setStretchLastSection(False)
        self.document_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        # Set font for table
        table_font = QFont()
        table_font.setPointSize(11)
        self.document_table.setFont(table_font)
        
        layout.addWidget(self.document_table)
        panel.setLayout(layout)
        return panel
    
    def _create_audit_panel(self) -> QWidget:
        """Create the right panel with audit display."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 0, 0, 0)
        
        # Document audit header
        self.document_audit_label = QLabel("Select a document to view its audit trail")
        self.document_audit_label.setStyleSheet("font-weight: bold; margin-bottom: 10px; font-size: 14px;")
        layout.addWidget(self.document_audit_label)
        
        # Audit display area
        self.audit_display = QTextEdit()
        self.audit_display.setReadOnly(True)
        self.audit_display.setFont(QFont("Consolas", 12))  # Larger monospace font
        self.audit_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.audit_display)
        
        panel.setLayout(layout)
        return panel
    
    def apply_filters(self):
        """Apply search filter and refresh display."""
        self.refresh_table()
    
    def refresh(self):
        """Refresh the document table and audit display with latest entries."""
        # Get all entries first
        all_entries = self.audit_manager.get_entries()
        
        # Filter entries by active request if available
        if self.request_manager:
            active_request = self.request_manager.get_active_request()
            if active_request:
                entries = [e for e in all_entries if e.request_id == active_request.id]
            else:
                entries = []  # No active request, show no entries
        else:
            entries = all_entries  # No request manager, show all entries
        
        # Update export button state
        count = len(entries)
        self.export_button.setEnabled(count > 0)
        
        # Build document data from audit entries and document store
        self._build_document_data(entries)
        
        # Refresh the table
        self.refresh_table()
        
        # Show appropriate message if no documents
        if not self.documents_with_audits:
            if self.request_manager:
                active_request = self.request_manager.get_active_request()
                if active_request:
                    self.audit_display.setText(f"No audit entries for request: {active_request.name}")
                    self.document_audit_label.setText(f"No audit entries for: {active_request.name}")
                else:
                    self.audit_display.setText("No active request selected.")
                    self.document_audit_label.setText("No active request selected")
            else:
                self.audit_display.setText("No audit entries yet. Start processing documents to see activity.")
                self.document_audit_label.setText("No documents with audit entries")
        else:
            # Select first document if none selected
            if len(self.documents_with_audits) > 0 and not self.current_document:
                self.document_table.selectRow(0)
    
    def _build_document_data(self, entries):
        """Build document data from audit entries and document store."""
        # Group entries by document
        documents_audit_data = {}
        for entry in entries:
            if entry.document_filename:
                if entry.document_filename not in documents_audit_data:
                    documents_audit_data[entry.document_filename] = {
                        'entries': [],
                        'ai_classification': None,
                        'human_decision': None,
                        'last_activity': None
                    }
                documents_audit_data[entry.document_filename]['entries'].append(entry)
                
                # Extract AI classification and human decision from entries
                if entry.event_type == 'classify' and entry.ai_result:
                    documents_audit_data[entry.document_filename]['ai_classification'] = entry.ai_result
                elif entry.event_type == 'review' and entry.user_decision:
                    documents_audit_data[entry.document_filename]['human_decision'] = entry.user_decision
                
                # Track latest activity
                if (documents_audit_data[entry.document_filename]['last_activity'] is None or
                    entry.timestamp > documents_audit_data[entry.document_filename]['last_activity']):
                    documents_audit_data[entry.document_filename]['last_activity'] = entry.timestamp
        
        # Convert to list format for table display
        self.documents_with_audits = []
        for doc_name, data in documents_audit_data.items():
            self.documents_with_audits.append({
                'filename': doc_name,
                'ai_classification': data['ai_classification'] or '-',
                'human_decision': data['human_decision'] or '-',
                'audit_count': len(data['entries']),
                'last_activity': data['last_activity'],
                'entries': data['entries']
            })
        
        # Sort by filename
        self.documents_with_audits.sort(key=lambda x: x['filename'])
    
    def refresh_table(self):
        """Refresh the document table with current data."""
        # Apply search filter
        search_text = self.search_input.text().lower()
        filtered_docs = self.documents_with_audits
        
        if search_text:
            filtered_docs = [
                doc for doc in self.documents_with_audits
                if search_text in doc['filename'].lower()
            ]
        
        # Update table
        self.document_table.setRowCount(len(filtered_docs))
        
        for row, doc_data in enumerate(filtered_docs):
            # Document name
            filename_item = QTableWidgetItem(doc_data['filename'])
            self.document_table.setItem(row, 0, filename_item)
            
            # AI Classification
            ai_item = QTableWidgetItem(doc_data['ai_classification'])
            self.document_table.setItem(row, 1, ai_item)
            
            # Human Decision
            human_item = QTableWidgetItem(doc_data['human_decision'])
            self.document_table.setItem(row, 2, human_item)
            
            # Audit Event Count
            count_item = QTableWidgetItem(f"{doc_data['audit_count']} events")
            self.document_table.setItem(row, 3, count_item)
            
            # Last Activity
            if doc_data['last_activity']:
                time_str = doc_data['last_activity'].strftime('%H:%M:%S')
                time_item = QTableWidgetItem(time_str)
            else:
                time_item = QTableWidgetItem('-')
            self.document_table.setItem(row, 4, time_item)
            
            # Store document data for selection
            filename_item.setData(Qt.ItemDataRole.UserRole, doc_data)
    
    def _on_document_selected(self):
        """Handle document selection change."""
        current_row = self.document_table.currentRow()
        if current_row >= 0:
            filename_item = self.document_table.item(current_row, 0)
            if filename_item:
                doc_data = filename_item.data(Qt.ItemDataRole.UserRole)
                if doc_data:
                    self.current_document = doc_data['filename']
                    self._update_document_audit_display_from_data(doc_data)
                    return
        
        # No valid selection
        self.current_document = None
        self.audit_display.setText("Select a document to view its audit trail")
        self.document_audit_label.setText("Select a document to view its audit trail")
    
    def _update_document_audit_display_from_data(self, doc_data):
        """Update the audit display using pre-loaded document data."""
        # Update header
        self.document_audit_label.setText(f"Audit Trail for: {doc_data['filename']}")
        
        doc_entries = doc_data['entries']
        if not doc_entries:
            self.audit_display.setText("No audit entries for this document")
            return
        
        # Sort entries chronologically
        sorted_entries = sorted(doc_entries, key=lambda e: e.timestamp)
        
        # Format and display entries
        lines = []
        for entry in sorted_entries:
            # Format: Time | Event | Details
            time_str = entry.timestamp.strftime('%H:%M:%S')
            event_str = entry.event_type.upper()
            details_str = entry.details
            
            # Add AI result and user decision if available
            if entry.ai_result:
                details_str += f" | AI: {entry.ai_result}"
            if entry.user_decision:
                details_str += f" | User: {entry.user_decision}"
            
            line = f"{time_str} | {event_str} | {details_str}"
            lines.append(line)
        
        # Set display text
        self.audit_display.setText('\n'.join(lines))
        
        # Scroll to bottom to show latest entries
        cursor = self.audit_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.audit_display.setTextCursor(cursor)
    
    def _update_document_audit_display(self):
        """Update the audit display for the selected document (fallback method)."""
        if not self.current_document:
            return
        
        # Get entries for this document
        all_entries = self.audit_manager.get_entries()
        doc_entries = [e for e in all_entries if e.document_filename == self.current_document]
        
        # Create data structure and call the main display method
        doc_data = {
            'filename': self.current_document,
            'entries': doc_entries
        }
        self._update_document_audit_display_from_data(doc_data)
    
    def _export_audit(self):
        """Export audit entries grouped by document to CSV file."""
        if self.audit_manager.get_entry_count() == 0:
            QMessageBox.information(
                self,
                "No Data",
                "No audit entries to export."
            )
            return
        
        try:
            # Get current working directory (repo folder)
            repo_folder = Path.cwd()
            
            # Create filename with timestamp
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"audit_log_{timestamp}.csv"
            export_path = repo_folder / filename
            
            # Export grouped by document
            self._export_grouped_by_document(export_path)
            
            # Show success message with option to open folder
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Export Complete")
            msg_box.setText(
                f"Audit log exported successfully!\n\n"
                f"Location: {repo_folder}\n"
                f"File: {filename}"
            )
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok
            )
            msg_box.setDefaultButton(QMessageBox.StandardButton.Open)
            
            result = msg_box.exec()
            if result == QMessageBox.StandardButton.Open:
                # Open the folder in the system file manager
                import platform
                import subprocess
                
                if platform.system() == "Windows":
                    subprocess.run(["explorer", str(repo_folder)])
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", str(repo_folder)])
                else:  # Linux and others
                    subprocess.run(["xdg-open", str(repo_folder)])
            
        except Exception as e:
            # Show error message
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export audit log:\n{str(e)}"
            )
    
    def _export_grouped_by_document(self, filepath: Path) -> None:
        """Export audit entries grouped by document to CSV file.
        
        Args:
            filepath: Path to save the CSV file
        """
        import csv
        
        # Get all entries
        all_entries = self.audit_manager.get_entries()
        
        # Group entries by document
        documents = {}
        for entry in all_entries:
            doc_name = entry.document_filename or "System Events"
            if doc_name not in documents:
                documents[doc_name] = []
            documents[doc_name].append(entry)
        
        # Write to CSV with document grouping
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['document', 'timestamp', 'request_id', 
                         'event', 'details', 'ai_result', 'user_decision']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()
            
            # Write entries grouped by document
            for doc_name in sorted(documents.keys()):
                doc_entries = sorted(documents[doc_name], key=lambda e: e.timestamp)
                
                for entry in doc_entries:
                    writer.writerow({
                        'document': doc_name,
                        'timestamp': entry.timestamp.isoformat(),
                        'request_id': entry.request_id,
                        'event': entry.event_type,
                        'details': entry.details,
                        'ai_result': entry.ai_result or '',
                        'user_decision': entry.user_decision or ''
                    })
    
    def refresh_request_context(self) -> None:
        """Refresh the audit display for the active request."""
        self._update_active_request_display()
        
        # Clear current selection and refresh data
        self.current_document = None
        self.refresh()
    
    def _update_active_request_display(self) -> None:
        """Update the active request label."""
        if self.request_manager:
            active_request = self.request_manager.get_active_request()
            if active_request:
                self.active_request_label.setText(f"Active Request: {active_request.name}")
            else:
                self.active_request_label.setText("No active request selected")
        else:
            self.active_request_label.setText("No request manager")

    def on_tab_selected(self):
        """Called when this tab is selected - refresh the display."""
        self.refresh()
    
    def _debug_add_test_entries(self):
        """Add some test entries for debugging (remove this later)."""
        if self.request_manager:
            active_request = self.request_manager.get_active_request()
            if active_request:
                # Add test entries
                self.audit_manager.log_embedding(
                    filename="test_doc.txt", 
                    request_id=active_request.id, 
                    success=True
                )
                self.audit_manager.log_classification(
                    filename="test_doc.txt",
                    result="responsive", 
                    confidence=0.85,
                    request_id=active_request.id
                )
                self.audit_manager.log_duplicate(
                    filename="test_doc.txt",
                    request_id=active_request.id,
                    is_duplicate=False
                )
                self.refresh()