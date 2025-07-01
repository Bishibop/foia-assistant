from pathlib import Path

from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ProcessingTab(QWidget):
    """Tab for document processing setup.

    Allows users to select a folder of documents and enter a FOIA request
    to process documents against. Provides controls to start the AI processing.
    """

    def __init__(self) -> None:
        super().__init__()
        self.selected_folder: Path | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Document Processing")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        # Folder selection section
        folder_group = QGroupBox("Select Documents Folder")
        folder_layout = QHBoxLayout()

        self.folder_label = QLineEdit()
        self.folder_label.setPlaceholderText("No folder selected")
        self.folder_label.setReadOnly(True)
        self.folder_label.setStyleSheet("padding: 5px; background-color: #f9f9f9;")

        self.select_folder_btn = QPushButton("Browse...")
        self.select_folder_btn.clicked.connect(self._select_folder)
        self.select_folder_btn.setStyleSheet(
            """
            QPushButton {
                padding: 5px 15px;
                background-color: #0066cc;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
        """
        )

        folder_layout.addWidget(self.folder_label, 1)
        folder_layout.addWidget(self.select_folder_btn)
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)

        # FOIA request section
        request_group = QGroupBox("FOIA Request")
        request_layout = QVBoxLayout()

        request_label = QLabel("Enter the FOIA request to process documents against:")
        request_layout.addWidget(request_label)

        self.request_text = QTextEdit()
        self.request_text.setPlaceholderText(
            "e.g., All emails and documents related to Project Blue Sky from January 2023 to December 2023"
        )
        self.request_text.setMaximumHeight(100)
        request_layout.addWidget(self.request_text)

        request_group.setLayout(request_layout)
        layout.addWidget(request_group)

        # Process button
        self.process_btn = QPushButton("Start Processing")
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self._start_processing)
        self.process_btn.setStyleSheet(
            """
            QPushButton {
                padding: 10px 30px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """
        )

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.process_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Add stretch to push everything to the top
        layout.addStretch()

        self.setLayout(layout)

        # Connect text change to enable/disable process button
        self.request_text.textChanged.connect(self._check_ready_to_process)

    def _select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Documents Folder", "", QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self.selected_folder = Path(folder)
            self.folder_label.setText(str(self.selected_folder))
            self._check_ready_to_process()

    def _check_ready_to_process(self) -> None:
        # Enable process button only if both folder and request are provided
        has_folder = self.selected_folder is not None
        has_request = len(self.request_text.toPlainText().strip()) > 0
        self.process_btn.setEnabled(has_folder and has_request)

    def _start_processing(self) -> None:
        # For now, just show a message
        QMessageBox.information(
            self,
            "Processing Started",
            f"Processing documents in:\n{self.selected_folder}\n\n"
            f"Against FOIA request:\n{self.request_text.toPlainText()}",
        )
