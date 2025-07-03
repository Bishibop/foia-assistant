"""
Audit Tab for FOIA Response Assistant

Provides a simple interface to view and export audit trail entries.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
    QLabel, QFileDialog, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ...processing.audit_manager import AuditManager
from ...constants import BUTTON_STYLE_PRIMARY


class AuditTab(QWidget):
    """Simple audit trail viewer and export interface."""
    
    def __init__(self, audit_manager: AuditManager):
        super().__init__()
        self.audit_manager = audit_manager
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the audit tab user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header section
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("Audit Trail")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # Entry count
        self.entry_count_label = QLabel("0 entries")
        self.entry_count_label.setStyleSheet("color: #666666; font-size: 12px;")
        
        # Export button
        self.export_button = QPushButton("Export Audit")
        self.export_button.setStyleSheet(BUTTON_STYLE_PRIMARY)
        self.export_button.clicked.connect(self._export_audit)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.entry_count_label)
        header_layout.addStretch()
        header_layout.addWidget(self.export_button)
        
        layout.addLayout(header_layout)
        
        # Audit display area
        self.audit_display = QTextEdit()
        self.audit_display.setReadOnly(True)
        self.audit_display.setFont(QFont("Consolas", 10))  # Monospace font
        self.audit_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        
        layout.addWidget(self.audit_display)
        
        # Refresh the display
        self.refresh()
    
    def refresh(self):
        """Refresh the audit display with latest entries."""
        entries = self.audit_manager.get_entries()
        
        # Update entry count
        count = len(entries)
        self.entry_count_label.setText(f"{count} entries")
        
        # Update export button state
        self.export_button.setEnabled(count > 0)
        
        if count == 0:
            self.audit_display.setText("No audit entries yet. Start processing documents to see activity.")
            return
        
        # Sort entries chronologically
        sorted_entries = sorted(entries, key=lambda e: e.timestamp)
        
        # Format and display entries
        lines = []
        for entry in sorted_entries:
            # Format: Time | Request | Document | Event | Details
            time_str = entry.timestamp.strftime('%H:%M:%S')
            request_str = entry.request_id[:8] if entry.request_id else 'N/A'  # Truncate for display
            doc_str = entry.document_filename or 'N/A'
            event_str = entry.event_type.upper()
            details_str = entry.details
            
            # Add AI result and user decision if available
            if entry.ai_result:
                details_str += f" | AI: {entry.ai_result}"
            if entry.user_decision:
                details_str += f" | User: {entry.user_decision}"
            
            line = f"{time_str} | {request_str} | {doc_str} | {event_str} | {details_str}"
            lines.append(line)
        
        # Set display text
        self.audit_display.setText('\n'.join(lines))
        
        # Scroll to bottom to show latest entries
        cursor = self.audit_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.audit_display.setTextCursor(cursor)
    
    def _export_audit(self):
        """Export all audit entries to CSV file."""
        if self.audit_manager.get_entry_count() == 0:
            QMessageBox.information(
                self,
                "No Data",
                "No audit entries to export."
            )
            return
        
        # Get save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Audit Log",
            str(Path.home() / "Documents" / "audit_log.csv"),
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            # Export to CSV
            self.audit_manager.export_csv(Path(file_path))
            
            # Show success message
            QMessageBox.information(
                self,
                "Export Complete",
                f"Audit log exported successfully to:\n{file_path}"
            )
            
        except Exception as e:
            # Show error message
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export audit log:\n{str(e)}"
            )
    
    def on_tab_selected(self):
        """Called when this tab is selected - refresh the display."""
        self.refresh()