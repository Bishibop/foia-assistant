from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ProcessedTab(QWidget):
    """Tab for viewing processed documents.

    Placeholder for Phase 6 implementation. Will display all reviewed
    documents with their final classifications and exemptions.
    """

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Processed Documents")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        # Placeholder message
        placeholder = QLabel("Processed documents view will be implemented in Phase 6")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(
            """
            QLabel {
                padding: 40px;
                background-color: #f0f0f0;
                border: 2px dashed #cccccc;
                border-radius: 5px;
                color: #666666;
                font-size: 16px;
            }
        """
        )

        layout.addWidget(placeholder)
        layout.addStretch()

        self.setLayout(layout)
