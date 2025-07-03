from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from ..constants import (
    TAB_FINALIZE,
    TAB_INTAKE,
    TAB_REVIEW,
    WINDOW_INITIAL_POSITION,
    WINDOW_INITIAL_SIZE,
    WINDOW_TITLE,
)
from .styles import MAIN_WINDOW_STYLE
from .tabs.finalize_tab import FinalizeTab
from .tabs.intake_tab import IntakeTab
from .tabs.review_tab import ReviewTab


class MainWindow(QMainWindow):
    """Main application window with tabbed interface.

    Provides the primary UI structure for the FOIA Response Assistant,
    organizing functionality into Processing, Review, and Processed tabs.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(
            WINDOW_INITIAL_POSITION[0],
            WINDOW_INITIAL_POSITION[1],
            WINDOW_INITIAL_SIZE[0],
            WINDOW_INITIAL_SIZE[1],
        )
        
        # Store source folder path
        self.source_folder = None

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self.intake_tab = IntakeTab()
        self.review_tab = ReviewTab()
        self.finalize_tab = FinalizeTab()

        # Add tabs to widget
        self.tab_widget.addTab(self.intake_tab, TAB_INTAKE)
        self.tab_widget.addTab(self.review_tab, TAB_REVIEW)
        self.tab_widget.addTab(self.finalize_tab, TAB_FINALIZE)

        # Connect signals between tabs
        self._connect_signals()

        # Apply styling
        self._apply_styling()

    def _connect_signals(self) -> None:
        """Connect signals between tabs."""
        # When folder is selected, store it
        self.intake_tab.folder_selected.connect(self._on_folder_selected)
        
        # When processing starts, clear all tabs
        self.intake_tab.processing_started.connect(self._clear_all_tabs)
        
        # When intake completes, send documents to review
        self.intake_tab.documents_processed.connect(self._on_documents_ready)

        # When review completes, send to finalize tab
        self.review_tab.review_completed.connect(self.finalize_tab.add_processed_document)
        
        # When all documents are reviewed, enable finalize buttons
        self.review_tab.all_documents_reviewed.connect(
            lambda: self.finalize_tab.set_all_documents_reviewed(True)
        )

    def _on_folder_selected(self, folder: Path) -> None:
        """Store the selected source folder."""
        self.source_folder = folder
        self.finalize_tab.set_source_folder(folder)
    
    def _clear_all_tabs(self) -> None:
        """Clear all documents from review and finalize tabs."""
        self.review_tab.clear_all()
        self.finalize_tab.clear_all()
    
    def _on_documents_ready(self, documents: list) -> None:
        """Handle documents ready for review."""
        # Add documents to review queue
        self.review_tab.add_documents(documents)

    def _apply_styling(self) -> None:
        self.setStyleSheet(MAIN_WINDOW_STYLE)
