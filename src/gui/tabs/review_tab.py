from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ReviewTab(QWidget):
    """Tab for reviewing document classifications.

    Placeholder for Phase 4 implementation. Will allow users to review
    AI classifications and make corrections.
    """

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Document Review")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        # Placeholder message
        placeholder = QLabel("Review interface will be implemented in Phase 4")
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
