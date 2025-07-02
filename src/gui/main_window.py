from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from ..constants import (
    TAB_PROCESSED,
    TAB_PROCESSING,
    TAB_REVIEW,
    WINDOW_INITIAL_POSITION,
    WINDOW_INITIAL_SIZE,
    WINDOW_TITLE,
)
from .styles import MAIN_WINDOW_STYLE
from .tabs.processed_tab import ProcessedTab
from .tabs.processing_tab import ProcessingTab
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

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self.processing_tab = ProcessingTab()
        self.review_tab = ReviewTab()
        self.processed_tab = ProcessedTab()

        # Add tabs to widget
        self.tab_widget.addTab(self.processing_tab, TAB_PROCESSING)
        self.tab_widget.addTab(self.review_tab, TAB_REVIEW)
        self.tab_widget.addTab(self.processed_tab, TAB_PROCESSED)

        # Connect signals between tabs
        self._connect_signals()

        # Apply styling
        self._apply_styling()

    def _connect_signals(self) -> None:
        """Connect signals between tabs."""
        # When processing completes, send documents to review
        self.processing_tab.documents_processed.connect(self._on_documents_ready)

        # When review completes, we'll handle in Phase 6
        # self.review_tab.review_completed.connect(self.processed_tab.add_document)

    def _on_documents_ready(self, documents: list) -> None:
        """Handle documents ready for review."""
        # Add documents to review queue
        self.review_tab.add_documents(documents)

    def _apply_styling(self) -> None:
        self.setStyleSheet(MAIN_WINDOW_STYLE)
