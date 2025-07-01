from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

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
        self.setWindowTitle("FOIA Response Assistant")
        self.setGeometry(100, 100, 1200, 800)

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
        self.tab_widget.addTab(self.processing_tab, "Processing")
        self.tab_widget.addTab(self.review_tab, "Review")
        self.tab_widget.addTab(self.processed_tab, "Processed")

        # Apply styling
        self._apply_styling()

    def _apply_styling(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                background-color: white;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0066cc;
            }
            QTabBar::tab:!selected {
                background-color: #f0f0f0;
            }
        """
        )
